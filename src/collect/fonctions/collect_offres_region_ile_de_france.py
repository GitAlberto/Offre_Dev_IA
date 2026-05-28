"""Module de collecte CSV des offres de la Region Ile-de-France.

Ce module a pour responsabilites :
- telecharger automatiquement le CSV officiel des offres de la Region Ile-de-France ;
- lire un fichier CSV local si on souhaite figer un snapshot ;
- mapper chaque ligne vers le schema brut d'offre du projet ;
- dedoublonner legerement les lignes sur un identifiant stable.

Ce qui est cense appeler ce module :
- `src/collect/collect.py` doit appeler `collect_offres_region_ile_de_france()` ;
- des tests isoles peuvent aussi l'utiliser directement.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_IDF_SOURCE_DIRECTORY = PROJECT_ROOT / "data" / "source_csv"
DEFAULT_IDF_CSV_PATH = DEFAULT_IDF_SOURCE_DIRECTORY / "region_ile_de_france.csv"
DEFAULT_IDF_CSV_EXPORT_URL = (
    "https://data.iledefrance.fr/api/explore/v2.1/catalog/datasets/"
    "offres-emploi-region-iledefrance/exports/csv?use_labels=true"
)
DEFAULT_IDF_TIMEOUT_SECONDS = 60


def resoudre_chemin_csv_region_ile_de_france(
    csv_path: str | Path | None = None,
) -> Path:
    """Resoudre le chemin du CSV IDF."""

    if csv_path:
        chemin = Path(csv_path).expanduser()
        if not chemin.is_absolute():
            chemin = PROJECT_ROOT / chemin
        return chemin

    if DEFAULT_IDF_CSV_PATH.exists():
        return DEFAULT_IDF_CSV_PATH

    if DEFAULT_IDF_SOURCE_DIRECTORY.exists():
        candidats = sorted(
            (
                path
                for path in DEFAULT_IDF_SOURCE_DIRECTORY.glob("*.csv")
                if path.is_file()
                and ("ile_de_france" in path.name.lower() or "idf" in path.name.lower())
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidats:
            return candidats[0]

    return DEFAULT_IDF_CSV_PATH


def telecharger_csv_region_ile_de_france(
    destination_path: Path = DEFAULT_IDF_CSV_PATH,
    export_url: str = DEFAULT_IDF_CSV_EXPORT_URL,
    timeout_seconds: int = DEFAULT_IDF_TIMEOUT_SECONDS,
) -> Path:
    """Telecharger automatiquement le CSV officiel des offres IDF."""

    destination_path.parent.mkdir(parents=True, exist_ok=True)

    response = requests.get(
        export_url,
        headers={"User-Agent": "JobRadar-IA/1.0"},
        timeout=timeout_seconds,
        stream=True,
    )
    response.raise_for_status()

    with destination_path.open("wb") as file:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                file.write(chunk)

    print(
        "Region Ile-de-France: CSV officiel telecharge depuis "
        f"{export_url} vers {destination_path}"
    )
    return destination_path


def normaliser_ligne_idf(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Nettoyer legerement les valeurs d'une ligne CSV IDF."""

    ligne = {}
    for key, value in raw_row.items():
        nom = str(key or "").replace("\ufeff", "").strip()
        if not nom:
            continue
        ligne[nom] = value.strip() if isinstance(value, str) else value
    return ligne


def premiere_valeur_non_vide_idf(
    row: dict[str, Any],
    *candidate_keys: str,
) -> str:
    """Retourner la premiere valeur non vide parmi plusieurs colonnes possibles."""

    for candidate_key in candidate_keys:
        valeur = row.get(candidate_key)
        if valeur is None:
            continue

        texte = str(valeur).strip()
        if texte:
            return texte

    return ""


def construire_identifiant_offre_idf(row: dict[str, Any]) -> str:
    """Construire un identifiant stable pour la deduplication locale."""

    identifiant = premiere_valeur_non_vide_idf(row, "id", "ref")
    if identifiant:
        return identifiant

    empreinte_source = " | ".join(
        morceau
        for morceau in (
            premiere_valeur_non_vide_idf(row, "Titre du poste"),
            premiere_valeur_non_vide_idf(
                row,
                "Nom de la collectivité",
                "Nom de l'établissement",
            ),
            premiere_valeur_non_vide_idf(row, "Date de mise en ligne"),
            premiere_valeur_non_vide_idf(row, "Localisation", "Commune du lycée"),
        )
        if morceau
    )
    if not empreinte_source:
        return ""

    digest = hashlib.sha1(empreinte_source.encode("utf-8")).hexdigest()
    return f"idf_{digest[:16]}"


def construire_nom_employeur_idf(row: dict[str, Any]) -> str:
    """Construire un nom d'employeur lisible."""

    return premiere_valeur_non_vide_idf(
        row,
        "Nom de la collectivité",
        "Entité",
        "Nom de l'établissement",
    )


def construire_localisation_idf(row: dict[str, Any]) -> str:
    """Construire une localisation lisible."""

    morceaux = []
    for bloc in (
        premiere_valeur_non_vide_idf(row, "Commune du lycée"),
        premiere_valeur_non_vide_idf(row, "Code postal du lycée"),
        premiere_valeur_non_vide_idf(row, "Localisation"),
    ):
        if bloc and bloc not in morceaux:
            morceaux.append(bloc)

    localisation = ", ".join(morceaux)
    if localisation:
        return localisation

    return premiere_valeur_non_vide_idf(
        row,
        "Lieu de Travail",
        "Adresse lieu de travail",
        "Adresse du lycée",
    )


def construire_description_idf(row: dict[str, Any]) -> str:
    """Construire une description texte compacte de l'offre."""

    blocs = []
    for bloc in (
        premiere_valeur_non_vide_idf(row, "Définition de la mission  (format texte)"),
        premiere_valeur_non_vide_idf(row, "Vos Missions (format texte)"),
        premiere_valeur_non_vide_idf(row, "Votre Profil (format texte)"),
        premiere_valeur_non_vide_idf(row, "Spécificités du poste (format texte)"),
        premiere_valeur_non_vide_idf(row, "Pied de page (format texte)"),
    ):
        if bloc and bloc not in blocs:
            blocs.append(bloc)

    return "\n\n".join(blocs)


def construire_competences_idf(row: dict[str, Any]) -> list[str]:
    """Construire une liste simple de competences / formations obligatoires."""

    bloc = premiere_valeur_non_vide_idf(row, "Formations obligatoires")
    if not bloc:
        return []

    competences = []
    for fragment in bloc.splitlines():
        valeur = fragment.strip(" -\t\r\n")
        if valeur and valeur not in competences:
            competences.append(valeur)
    return competences


def mapper_ligne_region_ile_de_france(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Convertir une ligne CSV IDF vers le schema brut d'offre du projet."""

    row = normaliser_ligne_idf(raw_row)

    external_id = construire_identifiant_offre_idf(row)
    title = premiere_valeur_non_vide_idf(row, "Titre du poste")
    company_name = construire_nom_employeur_idf(row)
    location_label = construire_localisation_idf(row)
    description = construire_description_idf(row)

    return {
        "source": "region_ile_de_france",
        "external_id": external_id,
        "title": title,
        "company": company_name,
        "company_name": company_name,
        "location": location_label,
        "location_label": location_label,
        "salary": "",
        "contract_type": premiere_valeur_non_vide_idf(row, "Type de contrat"),
        "published_at": premiere_valeur_non_vide_idf(row, "Date de mise en ligne"),
        "application_deadline": "",
        "url": "",
        "description": description,
        "skills": construire_competences_idf(row),
        "job_family": premiere_valeur_non_vide_idf(row, "Famille de métiers"),
        "job_label": premiere_valeur_non_vide_idf(row, "Fonction"),
        "category": premiere_valeur_non_vide_idf(row, "Catégorie"),
        "filiere": premiere_valeur_non_vide_idf(row, "Filière"),
        "domaine": premiere_valeur_non_vide_idf(row, "Domaine"),
        "speciality": premiere_valeur_non_vide_idf(row, "Spécialité"),
        "weekly_work_duration": premiere_valeur_non_vide_idf(
            row,
            "Durée hebdomadaire de travail",
        ),
        "contract_duration": premiere_valeur_non_vide_idf(row, "Durée du contrat"),
        "contract_start_date": premiere_valeur_non_vide_idf(
            row,
            "Date de début de contrat",
        ),
        "raw_payload": raw_row,
    }


def collect_offres_region_ile_de_france(
    csv_path: str | Path | None = None,
    auto_download_if_missing: bool = True,
    force_download: bool = False,
    export_url: str = DEFAULT_IDF_CSV_EXPORT_URL,
    timeout_seconds: int = DEFAULT_IDF_TIMEOUT_SECONDS,
) -> list[dict[str, Any]]:
    """Point d'entree principal pour la source CSV IDF."""

    resolved_path = resoudre_chemin_csv_region_ile_de_france(csv_path=csv_path)

    if force_download or not resolved_path.exists():
        if auto_download_if_missing:
            try:
                telecharger_csv_region_ile_de_france(
                    destination_path=resolved_path,
                    export_url=export_url,
                    timeout_seconds=timeout_seconds,
                )
            except (OSError, requests.RequestException) as exc:
                print(f"Region Ile-de-France: telechargement automatique impossible : {exc}")
                return []
        else:
            print(
                "Region Ile-de-France: aucun CSV local trouve et le telechargement automatique est desactive."
            )
            return []

    if resolved_path != DEFAULT_IDF_CSV_PATH:
        print(f"Region Ile-de-France: fichier detecte automatiquement : {resolved_path}")

    try:
        with resolved_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file, delimiter=";")

            offres: list[dict[str, Any]] = []
            identifiants_vus: set[str] = set()

            for raw_row in reader:
                if not isinstance(raw_row, dict):
                    continue

                if not any(str(value or "").strip() for value in raw_row.values()):
                    continue

                offre = mapper_ligne_region_ile_de_france(raw_row)
                external_id = str(offre.get("external_id") or "").strip()
                if not external_id:
                    continue

                if external_id in identifiants_vus:
                    continue

                identifiants_vus.add(external_id)
                offres.append(offre)
    except OSError as exc:
        print(f"Region Ile-de-France: impossible de lire le CSV : {exc}")
        return []
    except csv.Error as exc:
        print(f"Region Ile-de-France: parsing CSV impossible : {exc}")
        return []

    print(
        "Region Ile-de-France: "
        f"{len(offres)} offre(s) chargee(s) depuis {resolved_path}"
    )
    return offres


def build_argument_parser() -> argparse.ArgumentParser:
    """Construire une petite CLI pour lancer ce collecteur directement."""

    parser = argparse.ArgumentParser(
        description="Collecte les offres de la Region Ile-de-France depuis le CSV officiel."
    )
    parser.add_argument(
        "--csv-path",
        default=None,
        help=(
            "Chemin local du CSV a utiliser ou a ecrire. "
            "Par defaut : `data/source_csv/region_ile_de_france.csv`."
        ),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force le telechargement du dernier CSV officiel avant lecture.",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Desactive le telechargement automatique si le CSV local est absent.",
    )
    return parser


def main() -> None:
    """Executer le collecteur IDF directement depuis la ligne de commande."""

    parser = build_argument_parser()
    args = parser.parse_args()

    offres = collect_offres_region_ile_de_france(
        csv_path=args.csv_path,
        auto_download_if_missing=not args.no_download,
        force_download=args.refresh,
    )
    print(f"Region Ile-de-France: {len(offres)} offre(s) retournee(s) par le collecteur.")


if __name__ == "__main__":
    main()
