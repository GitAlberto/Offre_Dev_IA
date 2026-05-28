"""Module de collecte CSV des offres Choisir le Service Public.

Ce module a pour responsabilites :
- lire un fichier CSV local d'offres du portail Choisir le Service Public ;
- telecharger automatiquement le CSV officiel si aucun fichier local n'est disponible ;
- resoudre automatiquement le bon fichier si son nom telecharge contient une date ;
- mapper chaque ligne vers le schema brut d'offre du projet ;
- dedoublonner legerement les lignes sur un identifiant stable.

Ce qui est cense appeler ce module :
- `src/collect/collect.py` doit appeler
  `collect_offres_choisir_service_public()` ;
- des tests isoles peuvent aussi l'utiliser directement car il ne depend pas
  du reseau.

Limite importante :
- ce module prepare des offres brutes ;
- il ne remplace pas la normalisation finale de C3 ;
- il ne nettoie pas a lui seul les donnees metier.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CSP_SOURCE_DIRECTORY = PROJECT_ROOT / "data" / "source_csv"
DEFAULT_CSP_CSV_PATH = DEFAULT_CSP_SOURCE_DIRECTORY / "choisir_service_public.csv"
DEFAULT_CSP_DATASET_SLUG = "les-offres-diffusees-sur-choisir-le-service-public"
DEFAULT_CSP_DATASET_API_URL = (
    f"https://www.data.gouv.fr/api/1/datasets/{DEFAULT_CSP_DATASET_SLUG}/"
)
DEFAULT_CSP_TIMEOUT_SECONDS = 60


def resoudre_chemin_csv_choisir_service_public(
    csv_path: str | Path | None = None,
) -> Path:
    """Resoudre le chemin du CSV Choisir le Service Public.

    Comportement retenu :
    - si un chemin explicite est fourni, on l'utilise ;
    - sinon on privilegie `data/source_csv/choisir_service_public.csv` ;
    - si ce fichier n'existe pas, on prend le CSV le plus recent du dossier.
    """

    if csv_path:
        chemin = Path(csv_path).expanduser()
        if not chemin.is_absolute():
            chemin = PROJECT_ROOT / chemin
        return chemin

    if DEFAULT_CSP_CSV_PATH.exists():
        return DEFAULT_CSP_CSV_PATH

    if DEFAULT_CSP_SOURCE_DIRECTORY.exists():
        candidats = sorted(
            (
                path
                for path in DEFAULT_CSP_SOURCE_DIRECTORY.glob("*.csv")
                if path.is_file()
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidats:
            return candidats[0]

    return DEFAULT_CSP_CSV_PATH


def telecharger_metadonnees_csp(
    dataset_api_url: str = DEFAULT_CSP_DATASET_API_URL,
    timeout_seconds: int = DEFAULT_CSP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Telecharger les metadonnees du dataset officiel sur data.gouv.fr."""

    response = requests.get(
        dataset_api_url,
        headers={"User-Agent": "JobRadar-IA/1.0"},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Reponse JSON inattendue pour les metadonnees CSP.")
    return payload


def extraire_ressource_csv_csp(dataset_payload: dict[str, Any]) -> dict[str, Any] | None:
    """Choisir la meilleure ressource CSV principale dans les metadonnees du dataset."""

    resources = dataset_payload.get("resources", [])
    if not isinstance(resources, list):
        return None

    csv_resources = []
    for resource in resources:
        if not isinstance(resource, dict):
            continue

        resource_format = str(resource.get("format") or "").strip().lower()
        resource_url = str(resource.get("url") or "").strip()
        if resource_format != "csv" or not resource_url:
            continue

        csv_resources.append(resource)

    if not csv_resources:
        return None

    def resource_sort_key(resource: dict[str, Any]) -> tuple[str, str, str]:
        return (
            str(resource.get("last_modified") or ""),
            str(resource.get("created_at") or ""),
            str(resource.get("title") or ""),
        )

    csv_resources.sort(key=resource_sort_key, reverse=True)
    return csv_resources[0]


def telecharger_csv_csp_vers_source_csv(
    destination_path: Path = DEFAULT_CSP_CSV_PATH,
    dataset_api_url: str = DEFAULT_CSP_DATASET_API_URL,
    timeout_seconds: int = DEFAULT_CSP_TIMEOUT_SECONDS,
) -> Path:
    """Telecharger automatiquement le CSV officiel CSP et l'ecrire en local."""

    dataset_payload = telecharger_metadonnees_csp(
        dataset_api_url=dataset_api_url,
        timeout_seconds=timeout_seconds,
    )
    resource = extraire_ressource_csv_csp(dataset_payload)
    if resource is None:
        raise ValueError("Aucune ressource CSV exploitable n'a ete trouvee pour CSP.")

    download_url = str(resource.get("url") or "").strip()
    if not download_url:
        raise ValueError("La ressource CSV CSP ne contient pas d'URL de telechargement.")

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
        "Choisir le Service Public: CSV officiel telecharge depuis "
        f"{download_url} vers {destination_path}"
    )
    return destination_path


def detecter_delimiteur_csv(echantillon: str) -> str:
    """Detecter le delimiteur le plus probable pour le CSV source."""

    try:
        dialecte = csv.Sniffer().sniff(echantillon, delimiters=";,|\t")
        return dialecte.delimiter
    except csv.Error:
        occurrences = {
            ";": echantillon.count(";"),
            ",": echantillon.count(","),
            "\t": echantillon.count("\t"),
            "|": echantillon.count("|"),
        }
        meilleur_delimiteur, meilleur_score = max(
            occurrences.items(),
            key=lambda item: item[1],
        )
        if meilleur_score > 0:
            return meilleur_delimiteur

    return ","


def normaliser_nom_colonne(nom_colonne: str) -> str:
    """Rendre un nom de colonne plus robuste pour le mapping."""

    texte = unicodedata.normalize("NFKD", nom_colonne or "")
    texte = texte.encode("ascii", "ignore").decode("ascii")
    texte = texte.strip().lower()
    texte = re.sub(r"[^a-z0-9]+", "_", texte)
    texte = re.sub(r"_+", "_", texte)
    return texte.strip("_")


def normaliser_ligne_csv(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Normaliser les entetes et nettoyer legerement les valeurs de ligne."""

    ligne_normalisee: dict[str, Any] = {}

    for raw_key, raw_value in raw_row.items():
        nom_colonne = normaliser_nom_colonne(str(raw_key or ""))
        if not nom_colonne:
            continue

        valeur = raw_value.strip() if isinstance(raw_value, str) else raw_value
        if nom_colonne not in ligne_normalisee or not ligne_normalisee[nom_colonne]:
            ligne_normalisee[nom_colonne] = valeur

    return ligne_normalisee


def premiere_valeur_non_vide(
    row: dict[str, Any],
    *candidate_keys: str,
) -> str:
    """Retourner la premiere valeur non vide parmi plusieurs colonnes possibles."""

    for candidate_key in candidate_keys:
        valeur = row.get(normaliser_nom_colonne(candidate_key))
        if valeur is None:
            continue

        texte = str(valeur).strip()
        if texte:
            return texte

    return ""


def construire_nom_employeur(row: dict[str, Any]) -> str:
    """Construire un nom d'employeur lisible a partir du CSV source."""

    employeur_direct = premiere_valeur_non_vide(
        row,
        "employeur",
        "organisme_de_rattachement",
        "organisme_employeur",
        "nom_employeur",
        "entreprise",
        "organisme",
        "ministere_employeur",
    )
    if employeur_direct:
        return employeur_direct

    morceaux = []
    for bloc in (
        premiere_valeur_non_vide(row, "ministere", "ministere_libelle"),
        premiere_valeur_non_vide(row, "direction", "service", "service_affectation"),
    ):
        if bloc and bloc not in morceaux:
            morceaux.append(bloc)

    return " - ".join(morceaux)


def construire_localisation(row: dict[str, Any]) -> str:
    """Construire une localisation lisible meme si elle est eclatee en colonnes."""

    localisation_directe = premiere_valeur_non_vide(
        row,
        "localisation_du_poste",
        "lieu_d_affectation_sans_geolocalisation",
        "localisation",
        "lieu_de_travail",
        "lieu_d_affectation",
        "lieu",
        "adresse",
        "ville",
        "commune",
    )
    if localisation_directe:
        return localisation_directe

    morceaux = []
    for bloc in (
        premiere_valeur_non_vide(row, "commune", "ville", "localite"),
        premiere_valeur_non_vide(row, "departement", "nom_departement"),
        premiere_valeur_non_vide(row, "region", "nom_region"),
    ):
        if bloc and bloc not in morceaux:
            morceaux.append(bloc)

    return ", ".join(morceaux)


def extraire_competences(row: dict[str, Any]) -> list[str]:
    """Extraire une liste simple de competences si la source en porte."""

    bloc_competences = premiere_valeur_non_vide(
        row,
        "competences_attendues",
        "competences",
        "competence",
        "profil_recherche",
        "profil",
        "mots_cles",
    )
    if not bloc_competences:
        return []

    competences = []
    for fragment in re.split(r"[;,|/]", bloc_competences):
        libelle = fragment.strip()
        if libelle and libelle not in competences:
            competences.append(libelle)

    return competences


def construire_identifiant_offre(
    row: dict[str, Any],
    title: str,
    company_name: str,
    location_label: str,
    published_at: str,
    url: str,
) -> str:
    """Construire un identifiant stable pour la deduplication locale."""

    identifiant_source = premiere_valeur_non_vide(
        row,
        "id",
        "identifiant",
        "identifiant_offre",
        "offre_id",
        "uuid",
        "slug",
        "reference",
        "reference_offre",
        "numero_offre",
    )
    if identifiant_source:
        return identifiant_source

    if url:
        return url

    empreinte_source = " | ".join(
        morceau
        for morceau in (title, company_name, location_label, published_at)
        if morceau
    )
    if not empreinte_source:
        return ""

    digest = hashlib.sha1(empreinte_source.encode("utf-8")).hexdigest()
    return f"csp_{digest[:16]}"


def mapper_ligne_choisir_service_public(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Convertir une ligne CSV CSP vers le schema brut d'offre du projet."""

    row = normaliser_ligne_csv(raw_row)

    title = premiere_valeur_non_vide(
        row,
        "intitule_du_poste",
        "intitule",
        "intitule_poste",
        "titre",
        "libelle",
        "poste",
        "emploi",
    )
    company_name = construire_nom_employeur(row)
    location_label = construire_localisation(row)
    published_at = premiere_valeur_non_vide(
        row,
        "date_de_premiere_publication",
        "date_debut_de_publication_par_defaut",
        "date_publication",
        "date_de_publication",
        "datepublication",
        "published_at",
        "date_mise_en_ligne",
        "date_maj",
    )
    url = premiere_valeur_non_vide(
        row,
        "url",
        "lien",
        "url_offre",
        "url_annonce",
        "url_poste",
        "link",
    )
    description = premiere_valeur_non_vide(
        row,
        "description",
        "descriptif",
        "missions",
        "mission",
        "resume",
        "fiche_de_poste",
        "contexte",
    )
    salary = premiere_valeur_non_vide(
        row,
        "remuneration",
        "salaire",
        "salaire_indicatif",
        "fourchette_salaire",
        "traitement_indiciaire",
        "remuneration_brute",
    )
    contract_type = premiere_valeur_non_vide(
        row,
        "nature_de_contrat",
        "nature_de_l_emploi",
        "type_contrat",
        "nature_du_contrat",
        "statut",
        "type_emploi",
        "categorie_emploi",
        "contrat",
    )
    application_deadline = premiere_valeur_non_vide(
        row,
        "date_de_fin_de_publication_par_defaut",
        "date_limite_candidature",
        "date_limite",
        "date_cloture",
        "closing_date",
    )
    external_id = construire_identifiant_offre(
        row=row,
        title=title,
        company_name=company_name,
        location_label=location_label,
        published_at=published_at,
        url=url,
    )

    return {
        "source": "choisir_service_public",
        "external_id": external_id,
        "title": title,
        "company": company_name,
        "company_name": company_name,
        "location": location_label,
        "location_label": location_label,
        "salary": salary,
        "contract_type": contract_type,
        "published_at": published_at,
        "application_deadline": application_deadline,
        "url": url,
        "description": description,
        "skills": extraire_competences(row),
        "job_family": premiere_valeur_non_vide(row, "metier"),
        "public_sector": premiere_valeur_non_vide(row, "versant"),
        "category": premiere_valeur_non_vide(row, "categorie"),
        "telework": premiere_valeur_non_vide(row, "teletravail"),
        "management": premiere_valeur_non_vide(row, "management"),
        "raw_payload": raw_row,
    }


def collect_offres_choisir_service_public(
    csv_path: str | Path | None = None,
    auto_download_if_missing: bool = True,
    force_download: bool = False,
    dataset_api_url: str = DEFAULT_CSP_DATASET_API_URL,
    timeout_seconds: int = DEFAULT_CSP_TIMEOUT_SECONDS,
) -> list[dict[str, Any]]:
    """Point d'entree principal pour la source CSV Choisir le Service Public."""

    resolved_path = resoudre_chemin_csv_choisir_service_public(csv_path=csv_path)

    if force_download or not resolved_path.exists():
        if auto_download_if_missing:
            try:
                telecharger_csv_csp_vers_source_csv(
                    destination_path=resolved_path,
                    dataset_api_url=dataset_api_url,
                    timeout_seconds=timeout_seconds,
                )
            except (
                OSError,
                ValueError,
                requests.RequestException,
            ) as exc:
                print(
                    "Choisir le Service Public: telechargement automatique impossible : "
                    f"{exc}"
                )
                return []
        else:
            print(
                "Choisir le Service Public: aucun CSV local trouve et "
                "le telechargement automatique est desactive."
            )
            return []

    if resolved_path != DEFAULT_CSP_CSV_PATH:
        print(
            "Choisir le Service Public: fichier detecte automatiquement : "
            f"{resolved_path}"
        )

    try:
        with resolved_path.open("r", encoding="utf-8-sig", newline="") as file:
            sample = file.read(4096)
            file.seek(0)
            delimiter = detecter_delimiteur_csv(sample)
            reader = csv.DictReader(file, delimiter=delimiter)

            offres: list[dict[str, Any]] = []
            identifiants_vus: set[str] = set()

            for raw_row in reader:
                if not isinstance(raw_row, dict):
                    continue

                if not any(str(value or "").strip() for value in raw_row.values()):
                    continue

                offre = mapper_ligne_choisir_service_public(raw_row)
                external_id = str(offre.get("external_id") or "").strip()
                if not external_id:
                    continue

                if external_id in identifiants_vus:
                    continue

                identifiants_vus.add(external_id)
                offres.append(offre)
    except OSError as exc:
        print(f"Choisir le Service Public: impossible de lire le CSV : {exc}")
        return []
    except csv.Error as exc:
        print(f"Choisir le Service Public: parsing CSV impossible : {exc}")
        return []

    print(
        "Choisir le Service Public: "
        f"{len(offres)} offre(s) chargee(s) depuis {resolved_path}"
    )
    return offres


def build_argument_parser() -> argparse.ArgumentParser:
    """Construire une petite CLI pour lancer ce collecteur directement."""

    parser = argparse.ArgumentParser(
        description="Collecte les offres Choisir le Service Public depuis le CSV officiel."
    )
    parser.add_argument(
        "--csv-path",
        default=None,
        help=(
            "Chemin local du CSV a utiliser ou a ecrire. "
            "Par defaut : `data/source_csv/choisir_service_public.csv`."
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
    """Executer le collecteur CSP directement depuis la ligne de commande."""

    parser = build_argument_parser()
    args = parser.parse_args()

    offres = collect_offres_choisir_service_public(
        csv_path=args.csv_path,
        auto_download_if_missing=not args.no_download,
        force_download=args.refresh,
    )
    print(
        "Choisir le Service Public: "
        f"{len(offres)} offre(s) retournee(s) par le collecteur."
    )


if __name__ == "__main__":
    main()
