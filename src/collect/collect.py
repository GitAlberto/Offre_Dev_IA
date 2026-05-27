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
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    # Usage normal quand le module est importe comme package.
    from .fonctions import (
        collect_aggregates_hive,
        collect_offres_france_travail,
        collect_offres_postgresql_history,
        collect_offres_welcome_to_the_jungle,
        collect_reference_rome,
    )
except ImportError:
    # Usage pratique quand on lance directement :
    # `python src/collect/collect.py`
    from fonctions import (  # type: ignore
        collect_aggregates_hive,
        collect_offres_france_travail,
        collect_offres_postgresql_history,
        collect_offres_welcome_to_the_jungle,
        collect_reference_rome,
    )

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

SOURCE_KEYS = {
    "france_travail": "france_travail",
    "welcome_to_the_jungle": "welcome_to_the_jungle",
    "rome_reference": "rome_reference",
    "postgresql_history": "postgresql_history",
    "hive_aggregates": "hive_aggregates",
}


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
    query_wttj: str = "data engineer",
    days_back_postgresql: int = 30,
    france_travail_query_mode: str | None = None,
    france_travail_max_pages: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Collecter toutes les sources prevues par le projet.

    Cette fonction est le point d'entree principal de la phase C1.

    Ordre d'appel retenu :
    1. France Travail
    2. Welcome to the Jungle
    3. ROME
    4. PostgreSQL historique
    5. Hive aggregates

    Pourquoi cet ordre :
    - il reste proche de la roadmap du projet ;
    - il permet de lire facilement la collecte du plus "offres live" vers le
      plus "historique / analytique".

    Ce que cette fonction renvoie :
    - un dictionnaire `source -> lignes brutes`.

    Ce que cette fonction peut aussi faire :
    - sauvegarder un JSON brut global ;
    - sauvegarder un JSON par source si on active l'option correspondante.
    """

    charger_variables_environnement()

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
    france_travail_query_mode = (
        france_travail_query_mode
        or os.getenv(
            "FRANCE_TRAVAIL_QUERY_MODE",
            DEFAULT_FRANCE_TRAVAIL_QUERY_MODE,
        )
    )
    if france_travail_max_pages is None:
        france_travail_max_pages = lire_entier_positif_ou_aucune_limite(
            os.getenv(
                "FRANCE_TRAVAIL_MAX_PAGES",
                str(DEFAULT_FRANCE_TRAVAIL_MAX_PAGES),
            ),
            default=DEFAULT_FRANCE_TRAVAIL_MAX_PAGES,
        )
    database_url = os.getenv("DATABASE_URL", "")
    hive_host = os.getenv("HIVE_HOST", "localhost")
    hive_port = int(os.getenv("HIVE_PORT", "10000"))

    # On rend ces choix explicites ici pour que le lecteur comprenne tout de
    # suite la strategie retenue par l'orchestrateur :
    # - en mode demo, certaines sources peuvent privilegier un secours local ;
    # - hors mode demo, on laisse les connecteurs tenter leur comportement
    #   nominal, meme si pour l'instant ils restent encore au stade squelette.
    use_wttj_fallback = demo_mode
    use_postgresql_demo_seed = demo_mode
    use_hive_fallback = demo_mode

    payloads_par_source: dict[str, list[dict[str, Any]]] = {
        SOURCE_KEYS["france_travail"]: collect_offres_france_travail(
            client_id=france_travail_client_id,
            client_secret=france_travail_client_secret,
            max_results=france_travail_max_results,
            max_pages=france_travail_max_pages,
            timeout_seconds=france_travail_timeout_seconds,
            scope=france_travail_scope,
            query_mode=france_travail_query_mode,
            use_fallback_if_unavailable=demo_mode,
        ),
        SOURCE_KEYS["welcome_to_the_jungle"]: collect_offres_welcome_to_the_jungle(
            query=query_wttj,
            use_fallback=use_wttj_fallback,
        ),
        SOURCE_KEYS["rome_reference"]: collect_reference_rome(),
        SOURCE_KEYS["postgresql_history"]: collect_offres_postgresql_history(
            database_url=database_url,
            days_back=days_back_postgresql,
            use_demo_seed=use_postgresql_demo_seed,
        ),
        SOURCE_KEYS["hive_aggregates"]: collect_aggregates_hive(
            host=hive_host,
            port=hive_port,
            use_fallback=use_hive_fallback,
        ),
    }

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
        default="data engineer",
        help="Requete a utiliser pour Welcome to the Jungle.",
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

    collecter_toutes_les_sources(
        demo_mode=args.demo,
        save_raw_output=not args.no_save,
        save_per_source=args.save_per_source,
        query_wttj=args.query_wttj,
        days_back_postgresql=args.days_back_postgresql,
        france_travail_query_mode=args.france_travail_query_mode,
        france_travail_max_pages=lire_entier_positif_ou_aucune_limite(
            str(args.france_travail_max_pages)
            if args.france_travail_max_pages is not None
            else None,
            default=None,
        ),
    )


if __name__ == "__main__":
    main()
