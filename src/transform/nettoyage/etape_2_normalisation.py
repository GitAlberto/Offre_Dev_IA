"""Etape 2 de normalisation des donnees deja filtrees.

Ce module intervient apres `etape_1_filtrage.py`.

Pourquoi ce fichier s'appelle `etape_2_normalisation.py` :
- il intervient logiquement apres le filtrage brut ;
- il harmonise les lignes avant toute comparaison entre sources ;
- il prepare directement la deduplication finale.

Ce qu'il est cense faire plus tard :
- harmoniser les noms de champs importants ;
- convertir les dates dans un format stable ;
- transformer les salaires dans une representation comparable ;
- uniformiser les competences, les types de contrat et les localisations.

Ce qui est cense l'appeler :
- `src/transform/aggregate/aggregate.py`, apres la phase de nettoyage.

Ce que ce module n'est pas cense faire :
- la fusion finale de toutes les sources ;
- l'ecriture du dataset final CSV ;
- la logique de collecte.
"""

from __future__ import annotations

from typing import Any


def normaliser_ligne_source(
    nom_source: str,
    ligne_filtree: dict[str, Any],
) -> dict[str, Any]:
    """Normaliser une ligne provenant d'une source precise.

    Ce helper est volontairement simple a ce stade.

    Plus tard, il devra appliquer des regles source par source, par exemple :
    - convertir une date ISO, francaise ou timestamp vers un format commun ;
    - uniformiser les champs `title`, `titre`, `intitule` ;
    - rapprocher plusieurs representations d'un salaire.
    """

    ligne_normalisee = dict(ligne_filtree)

    # On garde une trace explicite de la source et de l'etape de traitement.
    ligne_normalisee["source"] = nom_source
    ligne_normalisee.setdefault("normalization_status", "pending_rules")

    return ligne_normalisee


def normaliser_payloads_filtres(
    payloads_filtres_par_source: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Normaliser l'ensemble des payloads filtres.

    Ce point d'entree est cense etre appele par :
    - `src/transform/aggregate/aggregate.py`.

    Ce qu'il renvoie :
    - un dictionnaire par source ;
    - avec des enregistrements prepares pour la comparaison transversale.
    """

    payloads_normalises: dict[str, list[dict[str, Any]]] = {}

    for nom_source, lignes_filtrees in payloads_filtres_par_source.items():
        payloads_normalises[nom_source] = [
            normaliser_ligne_source(
                nom_source=nom_source,
                ligne_filtree=ligne_filtree,
            )
            for ligne_filtree in lignes_filtrees
        ]

    return payloads_normalises
