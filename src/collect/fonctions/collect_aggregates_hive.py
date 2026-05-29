"""Module de collecte des agregats Hive.

Ce module a pour responsabilites :
- interroger Hive pour recuperer des agregats pre-calcules ;
- exposer un point d'entree distinct pour la source big data ;
- utiliser si besoin un instantane CSV local quand Hive n'est pas disponible.

Ce qui est cense appeler ce module :
- `src/collect/collect.py` doit appeler `collect_aggregates_hive()` ;
- `src/pipeline.py` doit normalement passer par l'orchestrateur de collecte
  plutot que d'utiliser ce module directement.

Ce que ce module est cense appeler en interne :
- un constructeur de requete Hive ;
- un client de connexion Hive ;
- un helper de mapping de lignes ;
- un lecteur de fichier de secours optionnel.

Limite importante :
- cette source sert des informations orientees agregats ;
- la couche API et la couche statistiques decideront plus tard comment les exposer.
"""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path
from typing import Any

try:
    from pyhive import hive
except ImportError:  # pragma: no cover - repli simple si pyhive manque
    hive = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_HIVE_FALLBACK_PATH = PROJECT_ROOT / "data" / "fallback" / "hive_agregats.csv"
DEFAULT_HIVE_QUERY_PATH = PROJECT_ROOT / "queries" / "hive" / "extraction_hive.hql"
DEFAULT_HIVE_DATABASE = "default"
DEFAULT_HIVE_AUTH = "NOSASL"
DEFAULT_HIVE_BEELINE_CONTAINER = "jobradar-hive"


def build_hive_aggregate_query(
    query_path: Path = DEFAULT_HIVE_QUERY_PATH,
) -> str:
    """Construire la requete Hive par defaut pour recuperer les agregats.

    Appelant attendu :
    - `collect_aggregates_hive()`.
    """

    if query_path.exists():
        query = query_path.read_text(encoding="utf-8").strip()
        if query:
            return query

    return (
        "SELECT competence, COUNT(*) AS nb, region "
        "FROM offres_historique "
        "GROUP BY competence, region"
    )


def map_hive_aggregate_row(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Convertir une ligne d'agregat Hive vers le schema brut du projet.

    Appelant attendu :
    - `collect_aggregates_hive()`.
    """

    return {
        "source": "hive_aggregates",
        "competence": raw_row.get("competence"),
        "count": raw_row.get("nb") or raw_row.get("count"),
        "region": raw_row.get("region"),
        "raw_payload": raw_row,
    }


def lire_fallback_hive(
    fallback_path: Path = DEFAULT_HIVE_FALLBACK_PATH,
) -> list[dict[str, Any]]:
    """Lire le CSV de secours Hive si present."""

    if not fallback_path.exists():
        return []

    with fallback_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return [
            map_hive_aggregate_row(dict(row))
            for row in reader
            if isinstance(row, dict)
        ]


def executer_requete_hive_via_beeline(
    query: str,
    database: str = DEFAULT_HIVE_DATABASE,
    auth: str = DEFAULT_HIVE_AUTH,
    container_name: str = DEFAULT_HIVE_BEELINE_CONTAINER,
) -> list[dict[str, Any]]:
    """Executer une requete Hive via `beeline` dans le conteneur Docker."""

    jdbc_url = f"jdbc:hive2://localhost:10000/{database}"
    auth_normalisee = str(auth or "").strip().lower()
    if auth_normalisee in {"nosasl", "none"}:
        jdbc_url += ";auth=none"
    query_compactee = " ".join(query.split())

    command = [
        "docker",
        "exec",
        container_name,
        "/opt/hive/bin/beeline",
        "--silent=true",
        "--showHeader=true",
        "--outputformat=tsv2",
        "-n",
        "hive",
        "-u",
        jdbc_url,
        "-e",
        query_compactee,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )
    prefixes_a_ignorer = (
        "SLF4J:",
        "[WARN]",
        "No such file or directory",
        "Connecting to ",
        "Connected to:",
        "Driver:",
        "Transaction isolation:",
        "Beeline version ",
        "Closing:",
        "INFO  :",
    )
    lignes_utiles = [
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip()
        and not line.strip().startswith(prefixes_a_ignorer)
    ]
    if not lignes_utiles:
        return []

    separateur = "\t" if "\t" in lignes_utiles[0] else None
    en_tetes = (
        [cell.strip() for cell in lignes_utiles[0].split("\t")]
        if separateur == "\t"
        else [lignes_utiles[0].strip()]
    )
    resultats: list[dict[str, Any]] = []

    for line in lignes_utiles[1:]:
        valeurs = (
            [cell.strip() for cell in line.split("\t")]
            if separateur == "\t"
            else [line.strip()]
        )
        if len(valeurs) != len(en_tetes):
            continue
        resultats.append(dict(zip(en_tetes, valeurs)))

    return resultats


def collect_aggregates_hive(
    host: str = "localhost",
    port: int = 10000,
    database: str = DEFAULT_HIVE_DATABASE,
    auth: str = DEFAULT_HIVE_AUTH,
    beeline_container: str = DEFAULT_HIVE_BEELINE_CONTAINER,
    use_fallback: bool = True,
    fallback_path: Path = DEFAULT_HIVE_FALLBACK_PATH,
) -> list[dict[str, Any]]:
    """Point d'entree principal pour la source d'agregats Hive.

    Appelant attendu :
    - `src/collect/collect.py`.

    Appels internes que cette fonction est censee faire :
    1. `build_hive_aggregate_query()`
    2. une connexion Hive vers `host:port`
    3. une execution de requete
    4. `map_hive_aggregate_row()` pour chaque agregat retourne
    5. un CSV de secours optionnel si Hive est indisponible pendant une demonstration

    Comportement actuel :
    - tente d'abord une lecture directe via `PyHive` ;
    - bascule automatiquement sur `beeline` dans Docker si la connexion Python
      a HiveServer2 echoue ;
    - peut enfin relire un CSV de secours en mode demonstration.
    """

    query = build_hive_aggregate_query()

    if hive is None:
        print("Hive: `pyhive` n'est pas installe, lecture Big Data ignoree.")
        if use_fallback:
            return lire_fallback_hive(fallback_path=fallback_path)
        return []

    try:
        with hive.Connection(
            host=host,
            port=port,
            username="hive",
            database=database,
            auth=auth,
        ) as connection:
            cursor = connection.cursor()
            cursor.execute(query)
            colonnes = [column[0] for column in cursor.description or []]
            lignes = cursor.fetchall()
    except Exception as exc:  # pragma: no cover - depend de l'environnement Docker
        print(f"Hive: echec de lecture PyHive : {exc}")
        try:
            lignes_beeline = executer_requete_hive_via_beeline(
                query=query,
                database=database,
                auth=auth,
                container_name=beeline_container,
            )
        except Exception as beeline_exc:  # pragma: no cover - depend de Docker
            print(f"Hive: echec de lecture beeline : {beeline_exc}")
        else:
            agregats_beeline = [
                map_hive_aggregate_row(raw_row)
                for raw_row in lignes_beeline
            ]
            print(
                "Hive: "
                f"{len(agregats_beeline)} agregat(s) relu(s) via beeline depuis {beeline_container}."
            )
            return agregats_beeline

        if use_fallback:
            lignes_fallback = lire_fallback_hive(fallback_path=fallback_path)
            if lignes_fallback:
                print(
                    "Hive: "
                    f"{len(lignes_fallback)} agregat(s) relu(s) depuis le CSV de secours."
                )
            return lignes_fallback
        return []

    agregats = [
        map_hive_aggregate_row(dict(zip(colonnes, row)))
        for row in lignes
    ]
    print(
        "Hive: "
        f"{len(agregats)} agregat(s) relu(s) depuis {host}:{port}/{database}."
    )
    return agregats
