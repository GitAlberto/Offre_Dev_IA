"""Module de collecte de l'historique PostgreSQL.

Ce module a pour responsabilites :
- interroger le stockage PostgreSQL historique ;
- reutiliser des offres deja collectees ;
- aider le futur pipeline a comparer les nouvelles donnees avec l'historique recent.

Ce qui est cense appeler ce module :
- `src/collect/collect.py` doit appeler `collect_offres_postgresql_history()` ;
- `src/pipeline.py` ne doit atteindre cette source qu'au travers de l'orchestrateur
  dans le flux normal.

Ce que ce module est cense appeler en interne :
- un constructeur de requete SQL ;
- une couche de connexion a la base ;
- un mapper qui convertit les lignes SQL en dictionnaires bruts.

Limite importante :
- ce module ne lit que l'historique ;
- la deduplication vis-a-vis des autres sources appartient a `src/transform/nettoyage/` ;
- le dataset final fusionne sera construit par `src/transform/aggregate/aggregate.py`.
"""

from __future__ import annotations

from typing import Any


def build_postgresql_history_query(days_back: int = 30) -> str:
    """Construire la requete SQL utilisee pour lire les offres recentes.

    Appelant attendu :
    - `collect_offres_postgresql_history()`.
    """

    return (
        "SELECT * "
        "FROM offres "
        f"WHERE date_publication >= NOW() - INTERVAL '{days_back} days'"
    )


def map_postgresql_history_row(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Convertir une ligne PostgreSQL vers le schema brut de source du projet.

    Appelant attendu :
    - `collect_offres_postgresql_history()`.
    """

    return {
        "source": "postgresql_history",
        "external_id": raw_row.get("id"),
        "title": raw_row.get("titre"),
        "company": raw_row.get("entreprise"),
        "location": raw_row.get("localisation"),
        "salary_min": raw_row.get("salaire_min"),
        "salary_max": raw_row.get("salaire_max"),
        "published_at": raw_row.get("date_publication"),
        "raw_payload": raw_row,
    }


def collect_offres_postgresql_history(
    database_url: str = "",
    days_back: int = 30,
    use_demo_seed: bool = True,
) -> list[dict[str, Any]]:
    """Point d'entree principal pour la source historique PostgreSQL.

    Appelant attendu :
    - `src/collect/collect.py`.

    Appels internes que cette fonction est censee faire :
    1. `build_postgresql_history_query()`
    2. une connexion PostgreSQL a partir de `database_url`
    3. une execution de requete
    4. `map_postgresql_history_row()` pour chaque ligne retournee
    5. un chemin de secours optionnel si aucun historique n'existe encore au premier lancement

    Comportement actuel :
    - documente l'orchestration future ;
    - retourne pour l'instant une liste vide.
    """

    query = build_postgresql_history_query(days_back=days_back)
    _ = database_url
    _ = query
    _ = use_demo_seed
    return []
