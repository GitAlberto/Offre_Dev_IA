"""Collecter Adzuna puis charger directement les offres dans PostgreSQL.

Objectif :
- faire d'Adzuna la source amont de simulation pour PostgreSQL ;
- conserver un chemin explicite et autonome pour peupler la table `offres` ;
- separer clairement la source SQL simulee des sources live de l'orchestrateur.
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
from src.collect.fonctions.collect_offres_adzuna import (
    ADZUNA_QUERY_GROUPS,
    DEFAULT_ADZUNA_COUNTRY,
    DEFAULT_ADZUNA_EXCLUDE_PREDICTED_SALARY,
    DEFAULT_ADZUNA_MAX_PAGES,
    DEFAULT_ADZUNA_QUERY_MODE,
    DEFAULT_ADZUNA_REQUIRE_SALARY,
    DEFAULT_ADZUNA_RESULTS_PER_PAGE,
    DEFAULT_ADZUNA_TIMEOUT_SECONDS,
    charger_variables_environnement_locales as charger_env_adzuna,
    collect_offres_adzuna,
    lire_booleen_adzuna,
)
from database.import_offres_postgresql import (
    DEFAULT_DATABASE_URL,
    importer_payload_collecte_dans_postgresql,
    vider_table_offres_postgresql,
)


RAW_OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "raw"


def build_argument_parser() -> argparse.ArgumentParser:
    """Construire le parseur CLI du pont Adzuna -> PostgreSQL."""

    parser = argparse.ArgumentParser(
        description="Collecter Adzuna puis charger les offres dans PostgreSQL.",
    )
    parser.add_argument(
        "--query",
        action="append",
        default=None,
        help="Requete Adzuna. Peut etre repetee.",
    )
    parser.add_argument(
        "--query-mode",
        choices=sorted(ADZUNA_QUERY_GROUPS),
        default=None,
        help="Strategie de requetes si `--query` n'est pas fournie.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Nombre maximum de pages a lire par requete.",
    )
    parser.add_argument(
        "--results-per-page",
        type=int,
        default=None,
        help="Nombre de resultats par page (max officiel observe : 50).",
    )
    parser.add_argument(
        "--allow-no-salary",
        action="store_true",
        help="Conserver aussi les annonces Adzuna sans salaire structure.",
    )
    parser.add_argument(
        "--exclude-predicted-salary",
        action="store_true",
        help="Ignorer les salaires marques comme predits par Adzuna.",
    )
    parser.add_argument(
        "--truncate-first",
        action="store_true",
        help="Vider la table `offres` avant de charger le nouveau snapshot Adzuna.",
    )
    parser.add_argument(
        "--no-save-raw",
        action="store_true",
        help="Ne pas sauvegarder le JSON brut Adzuna dans `data/raw/`.",
    )
    return parser


def main() -> None:
    """Executer la collecte Adzuna puis l'injection PostgreSQL."""

    charger_env_adzuna()
    parser = build_argument_parser()
    args = parser.parse_args()

    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    if not app_id.strip() or not app_key.strip():
        parser.error("Les variables `ADZUNA_APP_ID` et `ADZUNA_APP_KEY` sont requises.")

    query_mode = args.query_mode or os.getenv(
        "ADZUNA_QUERY_MODE",
        DEFAULT_ADZUNA_QUERY_MODE,
    )
    country = os.getenv("ADZUNA_COUNTRY", DEFAULT_ADZUNA_COUNTRY)
    results_per_page = args.results_per_page or int(
        os.getenv("ADZUNA_RESULTS_PER_PAGE", str(DEFAULT_ADZUNA_RESULTS_PER_PAGE))
    )
    max_pages = args.max_pages or int(
        os.getenv("ADZUNA_MAX_PAGES", str(DEFAULT_ADZUNA_MAX_PAGES))
    )
    timeout_seconds = int(
        os.getenv("ADZUNA_TIMEOUT_SECONDS", str(DEFAULT_ADZUNA_TIMEOUT_SECONDS))
    )
    require_salary = not args.allow_no_salary and lire_booleen_adzuna(
        os.getenv("ADZUNA_REQUIRE_SALARY"),
        DEFAULT_ADZUNA_REQUIRE_SALARY,
    )
    exclude_predicted_salary = args.exclude_predicted_salary or lire_booleen_adzuna(
        os.getenv("ADZUNA_EXCLUDE_PREDICTED_SALARY"),
        DEFAULT_ADZUNA_EXCLUDE_PREDICTED_SALARY,
    )

    offres = collect_offres_adzuna(
        app_id=app_id,
        app_key=app_key,
        queries=args.query,
        query_mode=query_mode,
        country=country,
        results_per_page=results_per_page,
        max_pages=max_pages,
        timeout_seconds=timeout_seconds,
        require_salary=require_salary,
        exclude_predicted_salary=exclude_predicted_salary,
    )
    payload = {"adzuna": offres}

    if not args.no_save_raw:
        output_path = construire_chemin_sortie_brute(
            source_name="adzuna",
            output_directory=RAW_OUTPUT_DIRECTORY,
        )
        sauvegarder_collecte_brute(
            payload=payload,
            output_path=output_path,
        )
        print(f"Adzuna: collecte brute sauvegardee: {output_path}")

    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    if not database_url.strip():
        parser.error("La variable `DATABASE_URL` est vide.")

    try:
        if args.truncate_first:
            vider_table_offres_postgresql(database_url=database_url)
            print("PostgreSQL: table `offres` videe avant chargement Adzuna.")

        nb_importees = importer_payload_collecte_dans_postgresql(
            database_url=database_url,
            payload_par_source=payload,
            sources_a_importer={"adzuna"},
        )
    except ModuleNotFoundError as exc:
        parser.error(str(exc))

    print(
        "Adzuna -> PostgreSQL: "
        f"{nb_importees} offre(s) importee(s) ou mise(s) a jour."
    )


if __name__ == "__main__":
    main()
