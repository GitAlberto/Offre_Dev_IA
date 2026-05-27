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

from pathlib import Path
from typing import Any


DEFAULT_HIVE_FALLBACK_PATH = Path("data/fallback/hive_agregats.csv")


def build_hive_aggregate_query() -> str:
    """Construire la requete Hive par defaut pour recuperer les agregats.

    Appelant attendu :
    - `collect_aggregates_hive()`.
    """

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
        "count": raw_row.get("nb"),
        "region": raw_row.get("region"),
        "raw_payload": raw_row,
    }


def collect_aggregates_hive(
    host: str = "localhost",
    port: int = 10000,
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
    - retourne une liste vide tant que le projet est encore en phase de squelette.
    """

    query = build_hive_aggregate_query()
    _ = host
    _ = port
    _ = query
    _ = use_fallback
    _ = fallback_path
    return []
