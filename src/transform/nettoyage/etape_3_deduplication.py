"""Etape 3 de deduplication des offres normalisees.

Ce module intervient apres la normalisation, une fois que plusieurs sources
partagent deja un schema plus comparable.

Pourquoi ce fichier s'appelle `etape_3_deduplication.py` :
- il arrive apres le filtrage et la normalisation ;
- il a besoin d'un schema deja harmonise pour comparer les offres ;
- il clot la phase `nettoyage/` avant l'agregation finale.

Ce qu'il est cense faire plus tard :
- comparer des offres proches entre sources ;
- eliminer les doublons evidents ;
- conserver une seule occurrence de reference lorsqu'une offre existe dans
  plusieurs systemes.

Ce qui est cense l'appeler :
- `src/transform/aggregate/aggregate.py`, juste avant la constitution du
  dataset final.

Ce que ce module n'est pas cense faire :
- nettoyer les lignes brutes ;
- normaliser les formats ;
- ecrire le fichier CSV final.
"""

from __future__ import annotations

from typing import Any


def construire_cle_deduplication(offre_normalisee: dict[str, Any]) -> tuple[Any, ...]:
    """Construire une cle simple de deduplication pour une offre.

    A ce stade, la cle reste volontairement conservative.

    Plus tard, elle pourra etre enrichie avec :
    - l'URL de l'offre ;
    - un identifiant externe ;
    - un titre normalise ;
    - le nom d'entreprise harmonise ;
    - la date de publication normalisee.
    """

    return (
        offre_normalisee.get("external_id"),
        offre_normalisee.get("title"),
        offre_normalisee.get("company"),
        offre_normalisee.get("published_at"),
    )


def dedoublonner_offres_normalisees(
    offres_normalisees: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Retirer les doublons evidents d'une liste d'offres normalisees.

    Ce point d'entree est cense etre appele par :
    - `src/transform/aggregate/aggregate.py`.

    Sortie attendue :
    - une liste d'offres finalement comparables ;
    - avec une seule occurrence par cle de deduplication.
    """

    cles_vues: set[tuple[Any, ...]] = set()
    offres_sans_doublons: list[dict[str, Any]] = []

    for offre in offres_normalisees:
        cle = construire_cle_deduplication(offre)

        if cle in cles_vues:
            continue

        cles_vues.add(cle)
        offres_sans_doublons.append(offre)

    return offres_sans_doublons
