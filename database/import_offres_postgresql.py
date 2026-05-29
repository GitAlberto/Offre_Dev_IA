"""Importer des collectes brutes JSON dans PostgreSQL.

Ce script sert de passerelle simple entre :
- les JSON bruts produits par `src/collect/collect.py` ;
- la table PostgreSQL `offres` consultee ensuite dans pgAdmin4.

Strategie retenue :
- on garde un schema denormalise et robuste pour faciliter les premiers tests ;
- on upsert sur `(source, external_id)` ;
- on conserve aussi `raw_payload` en JSONB pour ne perdre aucune information.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - message utilisateur plus propre
    psycopg = None
    dict_row = None
    Jsonb = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - repli simple si la dependance manque
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIRECTORY = PROJECT_ROOT / "data" / "raw"
DEFAULT_SCHEMA_SQL_PATH = PROJECT_ROOT / "database" / "migrations" / "001_create_offres.sql"
DEFAULT_DATABASE_URL = "postgresql://admin:secret@localhost:5433/jobradar"

OFFER_SOURCE_NAMES = {
    "adzuna",
    "bpce",
    "choisir_service_public",
    "france_travail",
    "la_bonne_alternance",
    "region_ile_de_france",
    "welcome_to_the_jungle",
}


def charger_variables_environnement_locales() -> None:
    """Charger le `.env` du projet si possible."""

    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env")


def resoudre_chemin_collecte_brute(input_path: str | Path | None = None) -> Path:
    """Trouver le JSON brut a importer."""

    if input_path:
        chemin = Path(input_path).expanduser()
        if not chemin.is_absolute():
            chemin = PROJECT_ROOT / chemin
        return chemin

    candidats = sorted(
        RAW_DIRECTORY.glob("raw_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidats:
        raise FileNotFoundError(
            "Aucun fichier `data/raw/raw_*.json` n'a ete trouve pour l'import PostgreSQL."
        )

    return candidats[0]


def resoudre_chemins_collecte_brute(
    input_paths: list[str] | None = None,
) -> list[Path]:
    """Resoudre un ou plusieurs chemins de collectes brutes."""

    if input_paths:
        return [resoudre_chemin_collecte_brute(input_path=path) for path in input_paths]

    return [resoudre_chemin_collecte_brute(input_path=None)]


def charger_payload_collecte(input_path: Path) -> dict[str, list[dict[str, Any]]]:
    """Charger le payload brut global produit par l'orchestrateur."""

    with input_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("Le JSON brut doit etre un objet `source -> lignes`.")

    return payload


def fusionner_payloads_collecte(
    payloads: list[dict[str, list[dict[str, Any]]]],
) -> dict[str, list[dict[str, Any]]]:
    """Fusionner plusieurs payloads `source -> lignes` en une seule structure."""

    payload_fusionne: dict[str, list[dict[str, Any]]] = {}

    for payload in payloads:
        for source_name, lignes in payload.items():
            if not isinstance(lignes, list):
                continue

            payload_fusionne.setdefault(source_name, [])
            payload_fusionne[source_name].extend(
                ligne for ligne in lignes if isinstance(ligne, dict)
            )

    return payload_fusionne


def aplatir_offres_collectees(
    payload_par_source: dict[str, list[dict[str, Any]]],
    sources_a_importer: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Ne garder que les vraies offres d'emploi a inserer en base."""

    offres: list[dict[str, Any]] = []

    for source_name, lignes in payload_par_source.items():
        if source_name not in OFFER_SOURCE_NAMES:
            continue

        if sources_a_importer is not None and source_name not in sources_a_importer:
            continue

        if not isinstance(lignes, list):
            continue

        for ligne in lignes:
            if not isinstance(ligne, dict):
                continue

            offre = dict(ligne)
            offre.setdefault("source", source_name)
            offres.append(offre)

    return offres


def construire_external_id_secours(offre: dict[str, Any]) -> str:
    """Construire un identifiant stable de secours si la source n'en fournit pas."""

    external_id = str(offre.get("external_id") or "").strip()
    if external_id:
        return external_id

    empreinte_source = " | ".join(
        morceau
        for morceau in (
            str(offre.get("source") or "").strip(),
            str(offre.get("title") or "").strip(),
            str(offre.get("company_name") or offre.get("company") or "").strip(),
            str(offre.get("location_label") or offre.get("location") or "").strip(),
            str(offre.get("published_at") or "").strip(),
            str(offre.get("url") or "").strip(),
        )
        if morceau
    )
    if not empreinte_source:
        return ""

    digest = hashlib.sha1(empreinte_source.encode("utf-8")).hexdigest()
    return f"fallback_{digest[:16]}"


def convertir_vers_datetime(raw_value: Any) -> datetime | None:
    """Convertir au mieux une date/heure heterogene vers un timestamp Python."""

    if raw_value is None:
        return None

    texte = str(raw_value).strip()
    if not texte:
        return None

    try:
        valeur = pd.to_datetime(texte, utc=True, errors="coerce")
    except Exception:  # pragma: no cover - repli defensif
        return None

    if pd.isna(valeur):
        return None

    return valeur.to_pydatetime()


def nettoyer_liste_competences(raw_value: Any) -> list[str]:
    """Normaliser la forme de `skills` avant insertion JSONB."""

    if raw_value is None:
        return []

    if isinstance(raw_value, list):
        competences: list[str] = []
        for element in raw_value:
            texte = str(element or "").strip()
            if texte and texte not in competences:
                competences.append(texte)
        return competences

    texte = str(raw_value).strip()
    if not texte:
        return []

    return [texte]


def mapper_offre_vers_ligne_postgresql(offre: dict[str, Any]) -> dict[str, Any]:
    """Preparer une ligne prete a etre upsertee dans PostgreSQL."""

    company_name = str(
        offre.get("company_name") or offre.get("company") or ""
    ).strip()
    location_label = str(
        offre.get("location_label") or offre.get("location") or ""
    ).strip()
    source_name = str(offre.get("source") or "").strip()
    external_id = construire_external_id_secours(offre)

    return {
        "source": source_name,
        "external_id": external_id,
        "title": str(offre.get("title") or "").strip(),
        "company": str(offre.get("company") or company_name).strip(),
        "company_name": company_name,
        "location": str(offre.get("location") or location_label).strip(),
        "location_label": location_label,
        "contract_type": str(offre.get("contract_type") or "").strip(),
        "published_at_raw": str(offre.get("published_at") or "").strip(),
        "published_at": convertir_vers_datetime(offre.get("published_at")),
        "application_deadline_raw": str(offre.get("application_deadline") or "").strip(),
        "application_deadline": convertir_vers_datetime(offre.get("application_deadline")),
        "salary": str(offre.get("salary") or "").strip(),
        "salary_min": str(offre.get("salary_min") or "").strip(),
        "salary_max": str(offre.get("salary_max") or "").strip(),
        "salary_is_predicted": offre.get("salary_is_predicted"),
        "url": str(offre.get("url") or "").strip(),
        "application_url": str(offre.get("application_url") or "").strip(),
        "description": str(offre.get("description") or "").strip(),
        "skills": nettoyer_liste_competences(offre.get("skills")),
        "job_family": str(offre.get("job_family") or "").strip(),
        "job_label": str(offre.get("job_label") or "").strip(),
        "job_code": str(offre.get("job_code") or "").strip(),
        "public_sector": str(offre.get("public_sector") or "").strip(),
        "category": str(offre.get("category") or "").strip(),
        "telework": str(offre.get("telework") or "").strip(),
        "contract_time": str(offre.get("contract_time") or "").strip(),
        "raw_payload": offre.get("raw_payload") if isinstance(offre.get("raw_payload"), dict) else offre,
    }


def charger_schema_sql(schema_sql_path: str | Path = DEFAULT_SCHEMA_SQL_PATH) -> str:
    """Lire le script SQL de creation de schema."""

    chemin = Path(schema_sql_path)
    if not chemin.is_absolute():
        chemin = PROJECT_ROOT / chemin

    with chemin.open("r", encoding="utf-8") as file:
        return file.read()


def garantir_schema_postgresql(
    database_url: str,
    schema_sql_path: str | Path = DEFAULT_SCHEMA_SQL_PATH,
) -> None:
    """Creer la table `offres` si elle n'existe pas encore."""

    if psycopg is None:
        raise ModuleNotFoundError(
            "Le module `psycopg` n'est pas installe. Lance `pip install -r requirements.txt`."
        )

    sql = charger_schema_sql(schema_sql_path=schema_sql_path)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
        connection.commit()


def vider_table_offres_postgresql(
    database_url: str,
    schema_sql_path: str | Path = DEFAULT_SCHEMA_SQL_PATH,
) -> None:
    """Vider completement la table `offres` apres avoir garanti son existence."""

    if psycopg is None:
        raise ModuleNotFoundError(
            "Le module `psycopg` n'est pas installe. Lance `pip install -r requirements.txt`."
        )

    garantir_schema_postgresql(
        database_url=database_url,
        schema_sql_path=schema_sql_path,
    )

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE offres RESTART IDENTITY;")
        connection.commit()


def importer_offres_dans_postgresql(
    database_url: str,
    offres: list[dict[str, Any]],
    schema_sql_path: str | Path = DEFAULT_SCHEMA_SQL_PATH,
) -> int:
    """Inserer ou mettre a jour une liste d'offres dans PostgreSQL."""

    if psycopg is None or Jsonb is None or dict_row is None:
        raise ModuleNotFoundError(
            "Le module `psycopg` n'est pas installe. Lance `pip install -r requirements.txt`."
        )

    if not offres:
        return 0

    garantir_schema_postgresql(
        database_url=database_url,
        schema_sql_path=schema_sql_path,
    )

    lignes = [mapper_offre_vers_ligne_postgresql(offre) for offre in offres]
    lignes = [
        ligne
        for ligne in lignes
        if ligne["source"] and ligne["external_id"]
    ]
    if not lignes:
        return 0

    query = """
        INSERT INTO offres (
            source,
            external_id,
            title,
            company,
            company_name,
            location,
            location_label,
            contract_type,
            published_at_raw,
            published_at,
            application_deadline_raw,
            application_deadline,
            salary,
            salary_min,
            salary_max,
            salary_is_predicted,
            url,
            application_url,
            description,
            skills,
            job_family,
            job_label,
            job_code,
            public_sector,
            category,
            telework,
            contract_time,
            raw_payload
        )
        VALUES (
            %(source)s,
            %(external_id)s,
            %(title)s,
            %(company)s,
            %(company_name)s,
            %(location)s,
            %(location_label)s,
            %(contract_type)s,
            %(published_at_raw)s,
            %(published_at)s,
            %(application_deadline_raw)s,
            %(application_deadline)s,
            %(salary)s,
            %(salary_min)s,
            %(salary_max)s,
            %(salary_is_predicted)s,
            %(url)s,
            %(application_url)s,
            %(description)s,
            %(skills)s,
            %(job_family)s,
            %(job_label)s,
            %(job_code)s,
            %(public_sector)s,
            %(category)s,
            %(telework)s,
            %(contract_time)s,
            %(raw_payload)s
        )
        ON CONFLICT (source, external_id)
        DO UPDATE SET
            title = EXCLUDED.title,
            company = EXCLUDED.company,
            company_name = EXCLUDED.company_name,
            location = EXCLUDED.location,
            location_label = EXCLUDED.location_label,
            contract_type = EXCLUDED.contract_type,
            published_at_raw = EXCLUDED.published_at_raw,
            published_at = EXCLUDED.published_at,
            application_deadline_raw = EXCLUDED.application_deadline_raw,
            application_deadline = EXCLUDED.application_deadline,
            salary = EXCLUDED.salary,
            salary_min = EXCLUDED.salary_min,
            salary_max = EXCLUDED.salary_max,
            salary_is_predicted = EXCLUDED.salary_is_predicted,
            url = EXCLUDED.url,
            application_url = EXCLUDED.application_url,
            description = EXCLUDED.description,
            skills = EXCLUDED.skills,
            job_family = EXCLUDED.job_family,
            job_label = EXCLUDED.job_label,
            job_code = EXCLUDED.job_code,
            public_sector = EXCLUDED.public_sector,
            category = EXCLUDED.category,
            telework = EXCLUDED.telework,
            contract_time = EXCLUDED.contract_time,
            raw_payload = EXCLUDED.raw_payload,
            updated_at = NOW()
    """

    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                query,
                [
                    {
                        **ligne,
                        "skills": Jsonb(ligne["skills"]),
                        "raw_payload": Jsonb(ligne["raw_payload"]),
                    }
                    for ligne in lignes
                ],
            )
        connection.commit()

    return len(lignes)


def importer_payload_collecte_dans_postgresql(
    database_url: str,
    payload_par_source: dict[str, list[dict[str, Any]]],
    sources_a_importer: set[str] | None = None,
    schema_sql_path: str | Path = DEFAULT_SCHEMA_SQL_PATH,
) -> int:
    """Aplatir un payload `source -> lignes` puis l'importer en base."""

    offres = aplatir_offres_collectees(
        payload_par_source=payload_par_source,
        sources_a_importer=sources_a_importer,
    )
    return importer_offres_dans_postgresql(
        database_url=database_url,
        offres=offres,
        schema_sql_path=schema_sql_path,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Construire le parseur CLI du script d'import PostgreSQL."""

    parser = argparse.ArgumentParser(
        description="Importer les JSON bruts collectes dans la table PostgreSQL `offres`.",
    )
    parser.add_argument(
        "--input-path",
        action="append",
        default=None,
        help=(
            "Chemin d'un JSON brut a importer. "
            "Peut etre repete pour fusionner plusieurs snapshots. "
            "Si non fourni, le script prend le `raw_*.json` le plus recent."
        ),
    )
    parser.add_argument(
        "--source",
        action="append",
        choices=sorted(OFFER_SOURCE_NAMES),
        default=None,
        help="Limiter l'import a une ou plusieurs sources d'offres.",
    )
    parser.add_argument(
        "--create-schema-only",
        action="store_true",
        help="Creer seulement la table PostgreSQL sans importer de donnees.",
    )
    parser.add_argument(
        "--truncate-first",
        action="store_true",
        help="Vider la table `offres` avant de recharger les nouvelles donnees.",
    )
    return parser


def main() -> None:
    """Executer le script d'import depuis la ligne de commande."""

    charger_variables_environnement_locales()
    parser = build_argument_parser()
    args = parser.parse_args()

    if psycopg is None:
        parser.error(
            "Le module `psycopg` n'est pas installe dans cet environnement Python. "
            "Installe les dependances du projet avec `pip install -r requirements.txt`."
        )

    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    if not database_url.strip():
        parser.error("La variable `DATABASE_URL` est vide.")

    if args.create_schema_only:
        garantir_schema_postgresql(database_url=database_url)
        print("PostgreSQL: schema `offres` cree ou deja present.")
        return

    input_paths = resoudre_chemins_collecte_brute(input_paths=args.input_path)
    payload = fusionner_payloads_collecte(
        [charger_payload_collecte(input_path) for input_path in input_paths]
    )

    if args.truncate_first:
        vider_table_offres_postgresql(database_url=database_url)
        print("PostgreSQL: table `offres` videe avant import.")

    offres = aplatir_offres_collectees(
        payload,
        sources_a_importer=set(args.source) if args.source else None,
    )
    nb_lignes = importer_offres_dans_postgresql(
        database_url=database_url,
        offres=offres,
    )
    input_paths_text = ", ".join(str(path) for path in input_paths)
    print(
        "PostgreSQL: "
        f"{nb_lignes} offre(s) importee(s) ou mise(s) a jour depuis {input_paths_text}"
    )


if __name__ == "__main__":
    main()
