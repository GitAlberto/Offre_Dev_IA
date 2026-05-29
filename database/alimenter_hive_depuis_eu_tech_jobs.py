"""Telecharger puis charger le dataset `eu-tech-jobs` dans Hive.

Objectif :
- peupler la source Big Data du projet avec un dataset volumineux ;
- conserver une table brute Parquet ;
- exposer une vue France et une vue `offres_historique` exploitable par les agregats.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HIVE_SOURCE_DIRECTORY = PROJECT_ROOT / "data" / "source_hive" / "eu_tech_jobs" / "latest"
HIVE_DATASET_ROOT_DIRECTORY = PROJECT_ROOT / "data" / "source_hive" / "eu_tech_jobs"
DATASET_PARQUET_URL = (
    "https://huggingface.co/datasets/Aramente/eu-tech-jobs/resolve/main/latest/jobs.parquet"
)
DATASET_METADATA_URL = (
    "https://huggingface.co/datasets/Aramente/eu-tech-jobs/resolve/main/latest/metadata.json"
)
LOCAL_PARQUET_PATH = HIVE_SOURCE_DIRECTORY / "jobs.parquet"
LOCAL_METADATA_PATH = HIVE_DATASET_ROOT_DIRECTORY / "metadata.json"
DEFAULT_HIVE_CONTAINER = "jobradar-hive"
DEFAULT_HIVE_DATABASE = "default"
DEFAULT_HQL_PATH = PROJECT_ROOT / "queries" / "hive" / "load_eu_tech_jobs.hql"


def telecharger_fichier(url: str, destination: Path, refresh: bool = False) -> Path:
    """Telecharger un fichier distant si besoin."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not refresh:
        return destination

    with requests.get(url, timeout=300, stream=True) as response:
        response.raise_for_status()
        with destination.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)

    return destination


def lire_hql_local(hql_path: Path = DEFAULT_HQL_PATH) -> str:
    """Lire le script HQL de creation des objets Hive."""

    return hql_path.read_text(encoding="utf-8")


def executer_hql_dans_hive(
    hql: str,
    database: str = DEFAULT_HIVE_DATABASE,
    container_name: str = DEFAULT_HIVE_CONTAINER,
) -> None:
    """Executer un script HQL multi-lignes dans le conteneur Hive."""

    command = [
        "docker",
        "exec",
        "-i",
        container_name,
        "/opt/hive/bin/beeline",
        "-u",
        f"jdbc:hive2://localhost:10000/{database}",
    ]
    subprocess.run(
        command,
        input=hql,
        text=True,
        check=True,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Construire le parseur CLI du script."""

    parser = argparse.ArgumentParser(
        description="Telecharger `eu-tech-jobs` puis le charger dans Hive.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Retelecharger le Parquet et les metadonnees meme si les fichiers existent deja.",
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Telecharger le dataset sans executer le chargement Hive.",
    )
    parser.add_argument(
        "--container-name",
        default=DEFAULT_HIVE_CONTAINER,
        help="Nom du conteneur Hive utilise pour lancer beeline.",
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_HIVE_DATABASE,
        help="Base Hive cible pour le chargement.",
    )
    return parser


def main() -> None:
    """Executer le pipeline de telechargement + chargement Hive."""

    args = build_argument_parser().parse_args()

    parquet_path = telecharger_fichier(
        url=DATASET_PARQUET_URL,
        destination=LOCAL_PARQUET_PATH,
        refresh=args.refresh,
    )
    metadata_path = telecharger_fichier(
        url=DATASET_METADATA_URL,
        destination=LOCAL_METADATA_PATH,
        refresh=args.refresh,
    )
    print(f"Hive eu-tech-jobs: Parquet pret: {parquet_path}")
    print(f"Hive eu-tech-jobs: metadonnees pretes: {metadata_path}")

    if args.download_only:
        return

    hql = lire_hql_local()
    executer_hql_dans_hive(
        hql=hql,
        database=args.database,
        container_name=args.container_name,
    )
    print(
        "Hive eu-tech-jobs: objets `eu_tech_jobs_raw`, `eu_tech_jobs_france` "
        "et `offres_historique` recrees."
    )


if __name__ == "__main__":
    main()
