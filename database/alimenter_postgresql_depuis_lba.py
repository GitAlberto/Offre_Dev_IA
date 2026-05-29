"""Collecter LBA puis charger directement les offres dans PostgreSQL.

Objectif :
- faire de La bonne alternance une source amont qui remplit la table SQL ;
- permettre ensuite a `postgresql_history` de simuler une vraie source
  historique relue depuis la base.

Flux retenu :
1. collecter les offres LBA via l'API officielle ;
2. sauvegarder un JSON brut du projet dans `data/raw/` ;
3. importer ces offres dans la table PostgreSQL `offres`.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collect.collect import (
    construire_chemin_sortie_brute,
    sauvegarder_collecte_brute,
)
from src.collect.fonctions.collect_offres_la_bonne_alternance import (
    DEFAULT_LBA_ENABLE_KEYWORD_FILTER,
    DEFAULT_LBA_INCLUDE_RECRUITER_OPPORTUNITIES,
    DEFAULT_LBA_ONLY_DIRECT_OFFERS,
    DEFAULT_LBA_TIMEOUT_SECONDS,
    charger_variables_environnement_locales as charger_env_lba,
    collect_offres_la_bonne_alternance,
    lire_booleen_lba,
)
from database.import_offres_postgresql import (
    DEFAULT_DATABASE_URL,
    importer_payload_collecte_dans_postgresql,
)


RAW_OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "raw"


def build_argument_parser() -> argparse.ArgumentParser:
    """Construire le parseur CLI du pont LBA -> PostgreSQL."""

    parser = argparse.ArgumentParser(
        description="Collecter LBA puis charger les offres dans PostgreSQL.",
    )
    parser.add_argument(
        "--no-save-raw",
        action="store_true",
        help="Ne pas sauvegarder le JSON brut LBA dans `data/raw/`.",
    )
    parser.add_argument(
        "--only-direct-offers",
        action="store_true",
        help="Ne garder que les offres deposees directement sur La bonne alternance.",
    )
    parser.add_argument(
        "--disable-keyword-filter",
        action="store_true",
        help="Importer toutes les offres LBA sans filtrage data/IA/BI/cloud.",
    )
    parser.add_argument(
        "--include-recruiter-opportunities",
        action="store_true",
        help="Inclure aussi les opportunites recruteur/candidature spontanee.",
    )
    return parser


def main() -> None:
    """Executer la collecte LBA puis l'injection PostgreSQL."""

    charger_env_lba()
    parser = build_argument_parser()
    args = parser.parse_args()

    api_key = os.getenv("LBA_API_KEY", "")
    if not api_key.strip():
        parser.error("La variable `LBA_API_KEY` est vide.")

    timeout_seconds = int(
        os.getenv("LBA_TIMEOUT_SECONDS", str(DEFAULT_LBA_TIMEOUT_SECONDS))
    )
    only_direct_offers = args.only_direct_offers or lire_booleen_lba(
        os.getenv("LBA_ONLY_DIRECT_OFFERS"),
        DEFAULT_LBA_ONLY_DIRECT_OFFERS,
    )
    enable_keyword_filter = not args.disable_keyword_filter and lire_booleen_lba(
        os.getenv("LBA_ENABLE_KEYWORD_FILTER"),
        DEFAULT_LBA_ENABLE_KEYWORD_FILTER,
    )
    include_recruiter_opportunities = (
        args.include_recruiter_opportunities
        or lire_booleen_lba(
            os.getenv("LBA_INCLUDE_RECRUITER_OPPORTUNITIES"),
            DEFAULT_LBA_INCLUDE_RECRUITER_OPPORTUNITIES,
        )
    )

    offres = collect_offres_la_bonne_alternance(
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        only_direct_offers=only_direct_offers,
        enable_keyword_filter=enable_keyword_filter,
        include_recruiter_opportunities=include_recruiter_opportunities,
    )

    payload = {"la_bonne_alternance": offres}

    if not args.no_save_raw:
        output_path = construire_chemin_sortie_brute(
            source_name="la_bonne_alternance",
            output_directory=RAW_OUTPUT_DIRECTORY,
        )
        sauvegarder_collecte_brute(
            payload=payload,
            output_path=output_path,
        )
        print(f"La bonne alternance: collecte brute sauvegardee: {output_path}")

    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    if not database_url.strip():
        parser.error("La variable `DATABASE_URL` est vide.")

    try:
        nb_importees = importer_payload_collecte_dans_postgresql(
            database_url=database_url,
            payload_par_source=payload,
            sources_a_importer={"la_bonne_alternance"},
        )
    except ModuleNotFoundError as exc:
        parser.error(str(exc))

    print(
        "La bonne alternance -> PostgreSQL: "
        f"{nb_importees} offre(s) importee(s) ou mise(s) a jour."
    )


if __name__ == "__main__":
    main()
