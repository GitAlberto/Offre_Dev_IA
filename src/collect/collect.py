"""Orchestrateur de collecte multi-sources.

Ce module est la premiere vraie couche de coordination du pipeline.

Son role est de :
- appeler chaque collecteur individuel situe dans `src/collect/fonctions/` ;
- recuperer les donnees brutes renvoyees par chaque source ;
- rassembler ces donnees dans une structure unique et previsible ;
- produire un resume lisible des volumes collectes ;
- sauvegarder la collecte brute dans `data/raw/` si on active l'ecriture.

Ce qui est cense appeler ce module :
- `python src/collect/collect.py` pour tester la collecte seule ;
- plus tard `src/pipeline.py` pour le flux complet ;
- eventuellement des tests d'integration sur la phase C1.

Ce que ce module n'est pas cense faire :
- nettoyer ou normaliser les donnees ;
- dedoublonner les offres ;
- ecrire le dataset final `clean_dataset.csv` ;
- inserer les donnees en base SQL.

Le principe de sortie retenu est :
- une structure en memoire de type `dict[str, list[dict]]` ;
- une cle par source ;
- des listes de lignes brutes pour chaque source ;
- une sauvegarde JSON optionnelle dans `data/raw/`.
"""

from __future__ import annotations

import argparse
import json
import os
from importlib import import_module
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - repli simple si la dependance manque
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "raw"
DEFAULT_FRANCE_TRAVAIL_SCOPE = ""
DEFAULT_FRANCE_TRAVAIL_MAX_RESULTS = 150
DEFAULT_FRANCE_TRAVAIL_MAX_PAGES = 20
DEFAULT_FRANCE_TRAVAIL_QUERY_MODE = "broad"
DEFAULT_FRANCE_TRAVAIL_TIMEOUT_SECONDS = 30
DEFAULT_WTTJ_QUERY_MODE = "focused"
DEFAULT_BPCE_CSV_PATH = "data/source_csv/bpce.csv"
DEFAULT_REGION_ILE_DE_FRANCE_CSV_PATH = "data/source_csv/region_ile_de_france.csv"

SOURCE_KEYS = {
    "france_travail": "france_travail",
    "welcome_to_the_jungle": "welcome_to_the_jungle",
    "bpce": "bpce",
    "region_ile_de_france": "region_ile_de_france",
    "postgresql_history": "postgresql_history",
    "hive_aggregates": "hive_aggregates",
}
SOURCE_IMPORT_SPECS = {
    SOURCE_KEYS["france_travail"]: (
        "collect_offres_france_travail",
        "collect_offres_france_travail",
    ),
    SOURCE_KEYS["welcome_to_the_jungle"]: (
        "collect_offres_welcome_to_the_jungle",
        "collect_offres_welcome_to_the_jungle",
    ),
    SOURCE_KEYS["bpce"]: (
        "collect_offres_bpce",
        "collect_offres_bpce",
    ),
    SOURCE_KEYS["region_ile_de_france"]: (
        "collect_offres_region_ile_de_france",
        "collect_offres_region_ile_de_france",
    ),
    SOURCE_KEYS["postgresql_history"]: (
        "collect_offres_postgresql_history",
        "collect_offres_postgresql_history",
    ),
    SOURCE_KEYS["hive_aggregates"]: (
        "collect_aggregates_hive",
        "collect_aggregates_hive",
    ),
}


def construire_nom_package_sources() -> str:
    """Retourner le nom de package a utiliser pour importer les collecteurs."""

    if __package__:
        return f"{__package__}.fonctions"

    return "fonctions"


def normaliser_sources_selectionnees(
    only_sources: list[str] | None = None,
    skip_sources: list[str] | None = None,
) -> list[str]:
    """Determiner les sources a executer en conservant l'ordre officiel."""

    sources_disponibles = list(SOURCE_IMPORT_SPECS.keys())

    if only_sources:
        sources_selectionnees = [
            source_name
            for source_name in sources_disponibles
            if source_name in set(only_sources)
        ]
    else:
        sources_selectionnees = list(sources_disponibles)

    if skip_sources:
        sources_ignorees = set(skip_sources)
        sources_selectionnees = [
            source_name
            for source_name in sources_selectionnees
            if source_name not in sources_ignorees
        ]

    if not sources_selectionnees:
        raise ValueError(
            "Aucune source selectionnee. Verifie `--only-source` et `--skip-source`."
        )

    return sources_selectionnees


def importer_fonction_collecte(source_name: str) -> Any:
    """Importer a la demande la fonction de collecte d'une source."""

    module_basename, function_name = SOURCE_IMPORT_SPECS[source_name]
    module_name = f"{construire_nom_package_sources()}.{module_basename}"

    try:
        module = import_module(module_name)
    except ImportError as error:
        raise ImportError(
            "Impossible d'importer le module de collecte pour la source "
            f"'{source_name}' ({module_name})."
        ) from error

    try:
        return getattr(module, function_name)
    except AttributeError as error:
        raise ImportError(
            f"Le module '{module_name}' ne definit pas la fonction '{function_name}'."
        ) from error


def charger_variables_environnement() -> None:
    """Charger le fichier `.env` local si `python-dotenv` est disponible.

    Pourquoi cette fonction existe :
    - l'orchestrateur a besoin de quelques parametres techniques ;
    - ces parametres vivent naturellement dans `.env` ;
    - on veut que la collecte fonctionne aussi bien en import Python qu'en
      execution directe depuis le terminal.
    """

    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env")


def construire_horodatage_fichier() -> str:
    """Retourner un horodatage stable pour les fichiers de sortie brute."""

    return datetime.now().strftime("%Y%m%d_%H%M%S")


def lire_entier_positif_ou_aucune_limite(
    raw_value: str | None,
    default: int | None,
) -> int | None:
    """Lire un entier positif depuis une variable d'environnement ou la CLI.

    Convention retenue :
    - valeur vide -> valeur par defaut ;
    - entier <= 0 -> aucune limite (`None`) ;
    - entier > 0 -> valeur conservee.
    """

    if raw_value is None or raw_value == "":
        return default

    parsed_value = int(raw_value)
    if parsed_value <= 0:
        return None

    return parsed_value


def construire_chemin_sortie_brute(
    source_name: str | None = None,
    output_directory: Path = RAW_OUTPUT_DIRECTORY,
) -> Path:
    """Construire le chemin d'ecriture d'une sortie brute.

    Regles retenues :
    - sans nom de source : on produit un fichier global de collecte ;
    - avec nom de source : on produit un fichier dedie a une source.

    Exemples :
    - `data/raw/raw_YYYYMMDD_HHMMSS.json`
    - `data/raw/france_travail_YYYYMMDD_HHMMSS.json`
    """

    timestamp = construire_horodatage_fichier()

    if source_name:
        filename = f"{source_name}_{timestamp}.json"
    else:
        filename = f"raw_{timestamp}.json"

    return output_directory / filename


def garantir_dossier_sortie(output_directory: Path = RAW_OUTPUT_DIRECTORY) -> None:
    """S'assurer que le dossier de sortie brute existe avant ecriture."""

    output_directory.mkdir(parents=True, exist_ok=True)


def convertir_pour_json(data: Any) -> Any:
    """Rendre une structure plus robuste pour la serialisation JSON.

    A ce stade, la plupart des objets sont deja des dictionnaires ou des listes.
    On garde tout de meme ce helper pour centraliser le comportement si des
    types supplementaires apparaissent plus tard.
    """

    if isinstance(data, dict):
        return {str(key): convertir_pour_json(value) for key, value in data.items()}

    if isinstance(data, list):
        return [convertir_pour_json(item) for item in data]

    if isinstance(data, Path):
        return str(data)

    return data


def sauvegarder_collecte_brute(
    payload: dict[str, list[dict[str, Any]]],
    output_path: Path,
) -> Path:
    """Sauvegarder une collecte brute dans un fichier JSON.

    Ce helper est cense etre appele par l'orchestrateur principal, pas par les
    collecteurs individuels.
    """

    garantir_dossier_sortie(output_directory=output_path.parent)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            convertir_pour_json(payload),
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    return output_path


def sauvegarder_collectes_par_source(
    payloads_par_source: dict[str, list[dict[str, Any]]],
    output_directory: Path = RAW_OUTPUT_DIRECTORY,
) -> list[Path]:
    """Sauvegarder une sortie JSON distincte pour chaque source.

    Cette option est utile surtout pour le debug, car elle permet de voir
    exactement ce que chaque connecteur renvoie avant toute transformation.
    """

    fichiers_crees: list[Path] = []

    for source_name, rows in payloads_par_source.items():
        output_path = construire_chemin_sortie_brute(
            source_name=source_name,
            output_directory=output_directory,
        )
        fichiers_crees.append(
            sauvegarder_collecte_brute(
                payload={source_name: rows},
                output_path=output_path,
            )
        )

    return fichiers_crees


def resumer_volumes_collectes(
    payloads_par_source: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    """Calculer un resume simple du nombre de lignes par source."""

    return {
        source_name: len(rows)
        for source_name, rows in payloads_par_source.items()
    }


def afficher_resume_collecte(
    payloads_par_source: dict[str, list[dict[str, Any]]],
) -> None:
    """Afficher un resume lisible de la collecte en console.

    Ce resume n'est pas indispensable au fonctionnement du code, mais il est
    tres utile pour :
    - voir rapidement si une source a renvoye quelque chose ;
    - comparer les volumes entre sources ;
    - disposer d'une sortie terminal exploitable pendant la soutenance.
    """

    summary = resumer_volumes_collectes(payloads_par_source)
    total_rows = sum(summary.values())

    print("Resume de collecte")
    print("------------------")

    for source_name, row_count in summary.items():
        print(f"- {source_name}: {row_count} ligne(s)")

    print(f"- total: {total_rows} ligne(s)")


def collecter_toutes_les_sources(
    demo_mode: bool = False,
    save_raw_output: bool = True,
    save_per_source: bool = False,
    query_wttj: list[str] | None = None,
    wttj_query_mode: str | None = None,
    bpce_csv_path: str | None = None,
    region_ile_de_france_csv_path: str | None = None,
    days_back_postgresql: int = 30,
    france_travail_query_mode: str | None = None,
    france_travail_max_pages: int | None = None,
    only_sources: list[str] | None = None,
    skip_sources: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Collecter toutes les sources prevues par le projet.

    Cette fonction est le point d'entree principal de la phase C1.

    Ordre d'appel retenu :
    1. France Travail
    2. Welcome to the Jungle
    3. BPCE
    4. Region Ile-de-France
    5. PostgreSQL historique
    6. Hive aggregates

    Pourquoi cet ordre :
    - il reste proche de la roadmap du projet ;
    - il permet de lire facilement la collecte du plus "offres live" vers le
      plus "historique / analytique".

    Ce que cette fonction renvoie :
    - un dictionnaire `source -> lignes brutes`.

    Ce que cette fonction peut aussi faire :
    - sauvegarder un JSON brut global ;
    - sauvegarder un JSON par source si on active l'option correspondante.
    - isoler une ou plusieurs sources pour faciliter les tests.
    """

    charger_variables_environnement()
    sources_selectionnees = normaliser_sources_selectionnees(
        only_sources=only_sources,
        skip_sources=skip_sources,
    )

    # On rend ces choix explicites ici pour que le lecteur comprenne tout de
    # suite la strategie retenue par l'orchestrateur :
    # - en mode demo, certaines sources peuvent privilegier un secours local ;
    # - hors mode demo, on laisse les connecteurs tenter leur comportement
    #   nominal, meme si pour l'instant ils restent encore au stade squelette.
    use_wttj_fallback = demo_mode
    use_postgresql_demo_seed = demo_mode
    use_hive_fallback = demo_mode

    if len(sources_selectionnees) != len(SOURCE_IMPORT_SPECS):
        print(
            "Sources selectionnees : "
            + ", ".join(sources_selectionnees)
        )

    payloads_par_source: dict[str, list[dict[str, Any]]] = {}

    if SOURCE_KEYS["france_travail"] in sources_selectionnees:
        collect_offres_france_travail = importer_fonction_collecte(
            SOURCE_KEYS["france_travail"]
        )
        france_travail_client_id = os.getenv("FRANCE_TRAVAIL_CLIENT_ID", "")
        france_travail_client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET", "")
        france_travail_scope = os.getenv(
            "FRANCE_TRAVAIL_SCOPE",
            DEFAULT_FRANCE_TRAVAIL_SCOPE,
        )
        france_travail_max_results = int(
            os.getenv(
                "FRANCE_TRAVAIL_MAX_RESULTS",
                str(DEFAULT_FRANCE_TRAVAIL_MAX_RESULTS),
            )
        )
        france_travail_timeout_seconds = int(
            os.getenv(
                "FRANCE_TRAVAIL_TIMEOUT_SECONDS",
                str(DEFAULT_FRANCE_TRAVAIL_TIMEOUT_SECONDS),
            )
        )
        france_travail_query_mode_effectif = (
            france_travail_query_mode
            or os.getenv(
                "FRANCE_TRAVAIL_QUERY_MODE",
                DEFAULT_FRANCE_TRAVAIL_QUERY_MODE,
            )
        )
        france_travail_max_pages_effectif = france_travail_max_pages
        if france_travail_max_pages_effectif is None:
            france_travail_max_pages_effectif = lire_entier_positif_ou_aucune_limite(
                os.getenv(
                    "FRANCE_TRAVAIL_MAX_PAGES",
                    str(DEFAULT_FRANCE_TRAVAIL_MAX_PAGES),
                ),
                default=DEFAULT_FRANCE_TRAVAIL_MAX_PAGES,
            )
        payloads_par_source[SOURCE_KEYS["france_travail"]] = collect_offres_france_travail(
            client_id=france_travail_client_id,
            client_secret=france_travail_client_secret,
            max_results=france_travail_max_results,
            max_pages=france_travail_max_pages_effectif,
            timeout_seconds=france_travail_timeout_seconds,
            scope=france_travail_scope,
            query_mode=france_travail_query_mode_effectif,
            use_fallback_if_unavailable=demo_mode,
        )

    if SOURCE_KEYS["welcome_to_the_jungle"] in sources_selectionnees:
        collect_offres_welcome_to_the_jungle = importer_fonction_collecte(
            SOURCE_KEYS["welcome_to_the_jungle"]
        )
        wttj_query_mode_effectif = (
            wttj_query_mode
            or os.getenv("WTTJ_QUERY_MODE", DEFAULT_WTTJ_QUERY_MODE)
        )
        payloads_par_source[SOURCE_KEYS["welcome_to_the_jungle"]] = (
            collect_offres_welcome_to_the_jungle(
                queries=query_wttj,
                query_mode=wttj_query_mode_effectif,
                use_fallback=use_wttj_fallback,
            )
        )

    if SOURCE_KEYS["bpce"] in sources_selectionnees:
        collect_offres_bpce = importer_fonction_collecte(
            SOURCE_KEYS["bpce"]
        )
        bpce_csv_path_effectif = (
            bpce_csv_path
            or os.getenv(
                "BPCE_CSV_PATH",
                DEFAULT_BPCE_CSV_PATH,
            )
        )
        payloads_par_source[SOURCE_KEYS["bpce"]] = (
            collect_offres_bpce(
                csv_path=bpce_csv_path_effectif,
            )
        )

    if SOURCE_KEYS["region_ile_de_france"] in sources_selectionnees:
        collect_offres_region_ile_de_france = importer_fonction_collecte(
            SOURCE_KEYS["region_ile_de_france"]
        )
        region_ile_de_france_csv_path_effectif = (
            region_ile_de_france_csv_path
            or os.getenv(
                "REGION_ILE_DE_FRANCE_CSV_PATH",
                DEFAULT_REGION_ILE_DE_FRANCE_CSV_PATH,
            )
        )
        payloads_par_source[SOURCE_KEYS["region_ile_de_france"]] = (
            collect_offres_region_ile_de_france(
                csv_path=region_ile_de_france_csv_path_effectif,
            )
        )

    if SOURCE_KEYS["postgresql_history"] in sources_selectionnees:
        collect_offres_postgresql_history = importer_fonction_collecte(
            SOURCE_KEYS["postgresql_history"]
        )
        database_url = os.getenv("DATABASE_URL", "")
        payloads_par_source[SOURCE_KEYS["postgresql_history"]] = (
            collect_offres_postgresql_history(
            database_url=database_url,
            days_back=days_back_postgresql,
            use_demo_seed=use_postgresql_demo_seed,
            )
        )

    if SOURCE_KEYS["hive_aggregates"] in sources_selectionnees:
        collect_aggregates_hive = importer_fonction_collecte(
            SOURCE_KEYS["hive_aggregates"]
        )
        hive_host = os.getenv("HIVE_HOST", "localhost")
        hive_port = int(os.getenv("HIVE_PORT", "10000"))
        payloads_par_source[SOURCE_KEYS["hive_aggregates"]] = collect_aggregates_hive(
            host=hive_host,
            port=hive_port,
            use_fallback=use_hive_fallback,
        )

    afficher_resume_collecte(payloads_par_source)

    if save_raw_output:
        global_output_path = construire_chemin_sortie_brute()
        sauvegarder_collecte_brute(
            payload=payloads_par_source,
            output_path=global_output_path,
        )
        print(f"Collecte brute globale sauvegardee: {global_output_path}")

    if save_per_source:
        output_paths = sauvegarder_collectes_par_source(payloads_par_source)
        for output_path in output_paths:
            print(f"Collecte brute par source sauvegardee: {output_path}")

    return payloads_par_source


def build_argument_parser() -> argparse.ArgumentParser:
    """Construire le parseur CLI de la phase de collecte."""

    source_choices = list(SOURCE_IMPORT_SPECS.keys())
    parser = argparse.ArgumentParser(
        description="Orchestre la collecte multi-sources du projet JobRadar IA.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Active le mode demonstration et privilegie les secours locaux quand c'est prevu.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Desactive l'ecriture du JSON brut global dans data/raw/.",
    )
    parser.add_argument(
        "--save-per-source",
        action="store_true",
        help="Ecrit aussi un fichier JSON brut separe pour chaque source.",
    )
    parser.add_argument(
        "--query-wttj",
        action="append",
        default=None,
        help=(
            "Requete WTTJ a lancer. Peut etre repetee pour enchainer "
            "plusieurs intitules de poste."
        ),
    )
    parser.add_argument(
        "--wttj-query-mode",
        choices=["legacy", "focused", "broad", "max_volume"],
        default=None,
        help=(
            "Strategie de requetes WTTJ. Ignoree si `--query-wttj` est fourni. "
            "`focused` est le bon mode par defaut pour enchainer plusieurs intitules data/IA."
        ),
    )
    parser.add_argument(
        "--bpce-csv-path",
        default=None,
        help=(
            "Chemin du CSV BPCE. "
            "Si non fourni, le collecteur cherche "
            "`data/source_csv/bpce.csv` puis le CSV BPCE le plus recent du dossier."
        ),
    )
    parser.add_argument(
        "--region-ile-de-france-csv-path",
        default=None,
        help=(
            "Chemin du CSV Region Ile-de-France. "
            "Si non fourni, le collecteur cherche "
            "`data/source_csv/region_ile_de_france.csv` puis le CSV IDF le plus recent du dossier."
        ),
    )
    parser.add_argument(
        "--only-source",
        action="append",
        choices=source_choices,
        help=(
            "Limiter le run a une source precise. "
            "Peut etre repete pour lancer plusieurs sources choisies."
        ),
    )
    parser.add_argument(
        "--skip-source",
        action="append",
        choices=source_choices,
        help=(
            "Ignorer une source precise sans modifier le code. "
            "Peut etre repete."
        ),
    )
    parser.add_argument(
        "--days-back-postgresql",
        type=int,
        default=30,
        help="Nombre de jours d'historique a demander a PostgreSQL.",
    )
    parser.add_argument(
        "--france-travail-query-mode",
        choices=["legacy", "focused", "broad", "max_volume"],
        default=None,
        help=(
            "Strategie de mots-cles France Travail : "
            "`legacy` pour la requete historique, "
            "`focused` pour plusieurs familles data/IA ciblees, "
            "`broad` pour une collecte large encore assez orientee data/IA, "
            "`max_volume` pour pousser le volume au maximum quitte a ajouter du bruit."
        ),
    )
    parser.add_argument(
        "--france-travail-max-pages",
        type=int,
        default=None,
        help=(
            "Nombre max de pages a lire par groupe de requetes France Travail. "
            "Utiliser 0 ou une valeur negative pour tenter toutes les pages disponibles."
        ),
    )
    return parser


def main() -> None:
    """Executer la collecte depuis la ligne de commande."""

    parser = build_argument_parser()
    args = parser.parse_args()

    try:
        collecter_toutes_les_sources(
            demo_mode=args.demo,
            save_raw_output=not args.no_save,
            save_per_source=args.save_per_source,
            query_wttj=args.query_wttj,
            wttj_query_mode=args.wttj_query_mode,
            bpce_csv_path=args.bpce_csv_path,
            region_ile_de_france_csv_path=args.region_ile_de_france_csv_path,
            days_back_postgresql=args.days_back_postgresql,
            france_travail_query_mode=args.france_travail_query_mode,
            france_travail_max_pages=lire_entier_positif_ou_aucune_limite(
                str(args.france_travail_max_pages)
                if args.france_travail_max_pages is not None
                else None,
                default=None,
            ),
            only_sources=args.only_source,
            skip_sources=args.skip_source,
        )
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
