"""Module de collecte CSV des offres Groupe BPCE.

Ce module a pour responsabilites :
- telecharger automatiquement le CSV officiel BPCE si aucun fichier local n'est disponible ;
- lire un fichier CSV local d'offres BPCE si on prefere figer un snapshot ;
- mapper chaque ligne vers le schema brut d'offre du projet ;
- dedoublonner legerement les lignes sur un identifiant stable.

Ce qui est cense appeler ce module :
- `src/collect/collect.py` doit appeler `collect_offres_bpce()` ;
- des tests isoles peuvent aussi l'utiliser directement car il ne depend que
  d'un CSV ou d'un telechargement HTTP simple.

Limite importante :
- ce module prepare des offres brutes ;
- il ne remplace pas la normalisation finale de C3 ;
- il ne dedoublonne pas les doublons inter-sources.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BPCE_SOURCE_DIRECTORY = PROJECT_ROOT / "data" / "source_csv"
DEFAULT_BPCE_CSV_PATH = DEFAULT_BPCE_SOURCE_DIRECTORY / "bpce.csv"
DEFAULT_BPCE_DATASET_SLUG = "groupe-bpce-offres-emploi-publiques"
DEFAULT_BPCE_DATASET_API_URL = (
    f"https://www.data.gouv.fr/api/1/datasets/{DEFAULT_BPCE_DATASET_SLUG}/"
)
DEFAULT_BPCE_TIMEOUT_SECONDS = 60


def resoudre_chemin_csv_bpce(
    csv_path: str | Path | None = None,
) -> Path:
    """Resoudre le chemin du CSV BPCE.

    Comportement retenu :
    - si un chemin explicite est fourni, on l'utilise ;
    - sinon on privilegie `data/source_csv/bpce.csv` ;
    - si ce fichier n'existe pas, on prend le CSV le plus recent du dossier
      qui ressemble a un export BPCE.
    """

    if csv_path:
        chemin = Path(csv_path).expanduser()
        if not chemin.is_absolute():
            chemin = PROJECT_ROOT / chemin
        return chemin

    if DEFAULT_BPCE_CSV_PATH.exists():
        return DEFAULT_BPCE_CSV_PATH

    if DEFAULT_BPCE_SOURCE_DIRECTORY.exists():
        candidats = sorted(
            (
                path
                for path in DEFAULT_BPCE_SOURCE_DIRECTORY.glob("*.csv")
                if path.is_file() and "bpce" in path.name.lower()
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidats:
            return candidats[0]

    return DEFAULT_BPCE_CSV_PATH


def telecharger_metadonnees_bpce(
    dataset_api_url: str = DEFAULT_BPCE_DATASET_API_URL,
    timeout_seconds: int = DEFAULT_BPCE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Telecharger les metadonnees du dataset officiel BPCE sur data.gouv.fr."""

    response = requests.get(
        dataset_api_url,
        headers={"User-Agent": "JobRadar-IA/1.0"},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Reponse JSON inattendue pour les metadonnees BPCE.")
    return payload


def extraire_ressource_csv_bpce(
    dataset_payload: dict[str, Any],
) -> dict[str, Any] | None:
    """Choisir la ressource CSV principale du dataset BPCE."""

    resources = dataset_payload.get("resources", [])
    if not isinstance(resources, list):
        return None

    ressources_csv = []
    for resource in resources:
        if not isinstance(resource, dict):
            continue

        resource_format = str(resource.get("format") or "").strip().lower()
        resource_url = str(resource.get("url") or "").strip()
        resource_title = str(resource.get("title") or "").strip().lower()
        if resource_format != "csv" or not resource_url:
            continue
        if "bpce" not in resource_title and "bpce" not in resource_url.lower():
            continue

        ressources_csv.append(resource)

    if not ressources_csv:
        return None

    ressources_csv.sort(
        key=lambda resource: (
            str(resource.get("last_modified") or ""),
            str(resource.get("created_at") or ""),
            str(resource.get("title") or ""),
        ),
        reverse=True,
    )
    return ressources_csv[0]


def telecharger_csv_bpce_vers_source_csv(
    destination_path: Path = DEFAULT_BPCE_CSV_PATH,
    dataset_api_url: str = DEFAULT_BPCE_DATASET_API_URL,
    timeout_seconds: int = DEFAULT_BPCE_TIMEOUT_SECONDS,
) -> Path:
    """Telecharger automatiquement le CSV officiel BPCE et l'ecrire en local."""

    dataset_payload = telecharger_metadonnees_bpce(
        dataset_api_url=dataset_api_url,
        timeout_seconds=timeout_seconds,
    )
    resource = extraire_ressource_csv_bpce(dataset_payload)
    if resource is None:
        raise ValueError("Aucune ressource CSV exploitable n'a ete trouvee pour BPCE.")

    download_url = str(resource.get("url") or "").strip()
    if not download_url:
        raise ValueError("La ressource CSV BPCE ne contient pas d'URL de telechargement.")

    destination_path.parent.mkdir(parents=True, exist_ok=True)

    response = requests.get(
        download_url,
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
        "BPCE: CSV officiel telecharge depuis "
        f"{download_url} vers {destination_path}"
    )
    return destination_path


def normaliser_ligne_bpce(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Nettoyer legerement les valeurs d'une ligne CSV BPCE."""

    return {
        str(key or "").strip(): value.strip() if isinstance(value, str) else value
        for key, value in raw_row.items()
        if str(key or "").strip()
    }


def premiere_valeur_non_vide_bpce(
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


def construire_localisation_bpce(row: dict[str, Any]) -> str:
    """Construire une localisation lisible a partir de la ville, region et pays."""

    morceaux = []
    for bloc in (
        premiere_valeur_non_vide_bpce(row, "Ville"),
        premiere_valeur_non_vide_bpce(row, "Région"),
        premiere_valeur_non_vide_bpce(row, "Pays"),
    ):
        if bloc and bloc not in morceaux:
            morceaux.append(bloc)

    return ", ".join(morceaux)


def construire_salaire_bpce(row: dict[str, Any]) -> str:
    """Construire un libelle de salaire simple a partir des bornes BPCE."""

    salaire_min = premiere_valeur_non_vide_bpce(row, "salary_min")
    salaire_max = premiere_valeur_non_vide_bpce(row, "salary_max")

    if salaire_min and salaire_max:
        return f"{salaire_min} - {salaire_max}"
    if salaire_min:
        return salaire_min
    if salaire_max:
        return salaire_max
    return ""


def construire_identifiant_offre_bpce(row: dict[str, Any]) -> str:
    """Construire un identifiant stable pour la deduplication locale."""

    reference = premiere_valeur_non_vide_bpce(
        row,
        "référence de l'offre",
        "reference de l'offre",
    )
    if reference:
        return reference

    view_url = premiere_valeur_non_vide_bpce(row, "Visualisation de l'offre")
    if view_url:
        return view_url

    empreinte_source = " | ".join(
        morceau
        for morceau in (
            premiere_valeur_non_vide_bpce(row, "Titre de l'annonce"),
            premiere_valeur_non_vide_bpce(row, "Entreprise", "Groupe"),
            premiere_valeur_non_vide_bpce(row, "Ville"),
            premiere_valeur_non_vide_bpce(row, "Date dernière modification"),
        )
        if morceau
    )
    if not empreinte_source:
        return ""

    digest = hashlib.sha1(empreinte_source.encode("utf-8")).hexdigest()
    return f"bpce_{digest[:16]}"


def mapper_ligne_bpce(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Convertir une ligne CSV BPCE vers le schema brut d'offre du projet."""

    row = normaliser_ligne_bpce(raw_row)

    external_id = construire_identifiant_offre_bpce(row)
    title = premiere_valeur_non_vide_bpce(row, "Titre de l'annonce")
    company_name = premiere_valeur_non_vide_bpce(row, "Entreprise", "Groupe")
    location_label = construire_localisation_bpce(row)
    salary = construire_salaire_bpce(row)

    return {
        "source": "bpce",
        "external_id": external_id,
        "title": title,
        "company": company_name,
        "company_name": company_name,
        "location": location_label,
        "location_label": location_label,
        "salary": salary,
        "salary_min": premiere_valeur_non_vide_bpce(row, "salary_min"),
        "salary_max": premiere_valeur_non_vide_bpce(row, "salary_max"),
        "contract_type": premiere_valeur_non_vide_bpce(row, "Type de contrat"),
        "published_at": premiere_valeur_non_vide_bpce(row, "Date dernière modification"),
        "application_deadline": "",
        "url": premiere_valeur_non_vide_bpce(row, "Visualisation de l'offre"),
        "application_url": premiere_valeur_non_vide_bpce(row, "URL candidature"),
        "description": premiere_valeur_non_vide_bpce(row, "description"),
        "skills": [],
        "job_family": premiere_valeur_non_vide_bpce(row, "Famille d'emploi"),
        "job_label": premiere_valeur_non_vide_bpce(row, "Emploi"),
        "job_code": premiere_valeur_non_vide_bpce(row, "jobcode"),
        "group_name": premiere_valeur_non_vide_bpce(row, "Groupe"),
        "telework": premiere_valeur_non_vide_bpce(row, "teletravail"),
        "degree": premiere_valeur_non_vide_bpce(row, "degree"),
        "recruiter_name": premiere_valeur_non_vide_bpce(
            row,
            "nom_recruteur_principal",
        ),
        "recruiter_email": premiere_valeur_non_vide_bpce(
            row,
            "email_recruteur_principal",
        ),
        "raw_payload": raw_row,
    }


def collect_offres_bpce(
    csv_path: str | Path | None = None,
    auto_download_if_missing: bool = True,
    force_download: bool = False,
    dataset_api_url: str = DEFAULT_BPCE_DATASET_API_URL,
    timeout_seconds: int = DEFAULT_BPCE_TIMEOUT_SECONDS,
) -> list[dict[str, Any]]:
    """Point d'entree principal pour la source CSV BPCE."""

    resolved_path = resoudre_chemin_csv_bpce(csv_path=csv_path)

    if force_download or not resolved_path.exists():
        if auto_download_if_missing:
            try:
                telecharger_csv_bpce_vers_source_csv(
                    destination_path=resolved_path,
                    dataset_api_url=dataset_api_url,
                    timeout_seconds=timeout_seconds,
                )
            except (
                OSError,
                ValueError,
                requests.RequestException,
            ) as exc:
                print(f"BPCE: telechargement automatique impossible : {exc}")
                return []
        else:
            print(
                "BPCE: aucun CSV local trouve et le telechargement automatique est desactive."
            )
            return []

    if resolved_path != DEFAULT_BPCE_CSV_PATH:
        print(f"BPCE: fichier detecte automatiquement : {resolved_path}")

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

                offre = mapper_ligne_bpce(raw_row)
                external_id = str(offre.get("external_id") or "").strip()
                if not external_id:
                    continue

                if external_id in identifiants_vus:
                    continue

                identifiants_vus.add(external_id)
                offres.append(offre)
    except OSError as exc:
        print(f"BPCE: impossible de lire le CSV : {exc}")
        return []
    except csv.Error as exc:
        print(f"BPCE: parsing CSV impossible : {exc}")
        return []

    print(f"BPCE: {len(offres)} offre(s) chargee(s) depuis {resolved_path}")
    return offres


def build_argument_parser() -> argparse.ArgumentParser:
    """Construire une petite CLI pour lancer ce collecteur directement."""

    parser = argparse.ArgumentParser(
        description="Collecte les offres BPCE depuis le CSV officiel."
    )
    parser.add_argument(
        "--csv-path",
        default=None,
        help=(
            "Chemin local du CSV a utiliser ou a ecrire. "
            "Par defaut : `data/source_csv/bpce.csv`."
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
    """Executer le collecteur BPCE directement depuis la ligne de commande."""

    parser = build_argument_parser()
    args = parser.parse_args()

    offres = collect_offres_bpce(
        csv_path=args.csv_path,
        auto_download_if_missing=not args.no_download,
        force_download=args.refresh,
    )
    print(f"BPCE: {len(offres)} offre(s) retournee(s) par le collecteur.")


if __name__ == "__main__":
    main()
