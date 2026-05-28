"""Module historique autour du referentiel ROME au format CSV.

Ce module a pour responsabilites :
- lire le fichier local de referentiel ROME en CSV ;
- preparer des lignes de reference brutes qui pourront plus tard enrichir les offres ;
- exposer un point d'entree clair dedie a cette nomenclature officielle.

Ce qui est cense appeler ce module :
- ce module n'est plus branche dans l'orchestrateur principal ;
- il reste disponible seulement comme piste de travail ou de test isole.

Ce que ce module est cense appeler en interne :
- un helper de resolution de chemin ;
- un lecteur CSV dans une future implementation ;
- un helper de mapping qui aligne les colonnes du fichier sur le schema du projet.

Limite importante :
- ce fichier lit une source de referentiel ;
- il ne doit pas faire lui-meme la fusion globale avec les offres d'emploi.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULT_ROME_CSV_PATH = Path("data/fallback/rome_codes.csv")


def resolve_rome_csv_path(csv_path: Path = DEFAULT_ROME_CSV_PATH) -> Path:
    """Resoudre l'emplacement du fichier CSV ROME.

    Appelant attendu :
    - `collect_reference_rome()`.

    Le but est de rendre explicite le futur chargement de fichier et de le
    rediriger facilement si le projet supporte plus tard des chemins personnalises.
    """

    return csv_path


def map_rome_row(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Convertir une ligne CSV ROME vers le schema brut de reference du projet.

    Appelant attendu :
    - `collect_reference_rome()`.
    """

    return {
        "source": "rome_csv",
        "rome_code": raw_row.get("rome_code"),
        "job_family": raw_row.get("job_family"),
        "skill_label": raw_row.get("skill_label"),
        "raw_payload": raw_row,
    }


def collect_reference_rome(
    csv_path: Path = DEFAULT_ROME_CSV_PATH,
) -> list[dict[str, Any]]:
    """Point d'entree principal pour la source ROME en CSV.

    Appelant attendu :
    - des tests isoles eventuels si cette piste est reprise plus tard.

    Appels internes que cette fonction est censee faire :
    1. `resolve_rome_csv_path()`
    2. une lecture du fichier CSV
    3. `map_rome_row()` sur chaque ligne du fichier de reference

    Sortie attendue :
    - une liste de dictionnaires bruts de reference ;
    - un dictionnaire par ligne du fichier ROME.

    Comportement actuel :
    - retourne une liste vide ;
    - la collecte principale du projet privilegie desormais des sources
      d'offres d'emploi plutot qu'un referentiel.
    """

    resolved_path = resolve_rome_csv_path(csv_path=csv_path)
    _ = resolved_path
    return []
