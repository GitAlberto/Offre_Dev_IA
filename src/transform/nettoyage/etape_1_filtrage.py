"""Etape 1 de filtrage dans le nettoyage des donnees collecteess.

Ce module intervient juste apres la collecte brute.

Pourquoi ce fichier s'appelle `etape_1_filtrage.py` :
- il represente la premiere etape de la phase `nettoyage/` ;
- il doit etre execute avant toute normalisation ;
- il rend l'ordre du pipeline visible directement dans l'arborescence.

Ce qu'il est cense faire plus tard :
- eliminer les lignes completement inutilisables ;
- ignorer les objets vides ou mal formes ;
- retirer les offres qui n'ont pas les informations minimales requises ;
- preparer un jeu de donnees plus propre pour la normalisation.

Ce qui est cense l'appeler :
- `src/transform/aggregate/aggregate.py` pendant la transformation complete.

Ce que ce module n'est pas cense faire :
- il ne doit pas dedoublonner les offres entre sources ;
- il ne doit pas ecrire le dataset final sur disque ;
- il ne doit pas faire la fusion finale de toutes les sources.
"""

from __future__ import annotations

from typing import Any


def filtrer_lignes_source(
    nom_source: str,
    lignes_brutes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filtrer les lignes d'une source unique.

    Attendu plus tard :
    - verifier que chaque element est bien un dictionnaire exploitable ;
    - eliminer les lignes vides ;
    - retirer les enregistrements trop incomplets pour la suite du pipeline.

    Ce helper est cense etre appele uniquement par
    `filtrer_payloads_collectes()`.
    """

    lignes_filtrees: list[dict[str, Any]] = []

    for ligne in lignes_brutes:
        # A ce stade du squelette, on applique seulement des regles minimales
        # et sans risque. Les criteres metier exacts viendront plus tard.
        if not isinstance(ligne, dict):
            continue
        if not ligne:
            continue

        # On conserve une copie pour eviter de modifier les objets d'origine.
        ligne_preparee = dict(ligne)
        ligne_preparee.setdefault("source", nom_source)
        lignes_filtrees.append(ligne_preparee)

    return lignes_filtrees


def filtrer_payloads_collectes(
    payloads_par_source: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Filtrer l'ensemble des sorties brutes de collecte.

    Ce point d'entree est cense etre appele par :
    - `src/transform/aggregate/aggregate.py`.

    Ce qu'il recoit :
    - un dictionnaire indexe par nom de source ;
    - chaque valeur est une liste de dictionnaires bruts.

    Ce qu'il renvoie :
    - la meme structure generale ;
    - mais avec des lignes invalides retirees ou preparees pour la suite.
    """

    payloads_filtres: dict[str, list[dict[str, Any]]] = {}

    for nom_source, lignes_brutes in payloads_par_source.items():
        payloads_filtres[nom_source] = filtrer_lignes_source(
            nom_source=nom_source,
            lignes_brutes=lignes_brutes,
        )

    return payloads_filtres
