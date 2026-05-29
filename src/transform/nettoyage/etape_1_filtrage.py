"""Etape 1 : filtrage metier et technique des payloads collectes.

Cette etape retire :
- les lignes vides ou mal formees ;
- les enregistrements qui ne ressemblent pas a de vraies offres ;
- les annonces hors perimetre data / IA / BI / cloud ;
- les agregats Hive incomplets.
"""

from __future__ import annotations

from typing import Any

from .utils import (
    AGGREGATE_SOURCE_NAMES,
    OFFER_SOURCE_NAMES,
    evaluer_perimetre_metier,
    nettoyer_texte,
)


def filtrer_lignes_source(
    nom_source: str,
    lignes_brutes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filtrer les lignes d'une source unique avec des regles explicites."""

    lignes_filtrees: list[dict[str, Any]] = []
    invalides = 0
    hors_perimetre = 0

    for ligne in lignes_brutes:
        if not isinstance(ligne, dict) or not ligne:
            invalides += 1
            continue

        ligne_preparee = dict(ligne)
        ligne_preparee.setdefault("source", nom_source)

        if nom_source in AGGREGATE_SOURCE_NAMES:
            competence = nettoyer_texte(ligne_preparee.get("competence"))
            region = nettoyer_texte(ligne_preparee.get("region"))
            count = ligne_preparee.get("count") or ligne_preparee.get("nb")
            if not competence or not region or count in (None, ""):
                invalides += 1
                continue
            ligne_preparee["record_kind"] = "aggregate"
            ligne_preparee["filter_status"] = "kept_aggregate"
            lignes_filtrees.append(ligne_preparee)
            continue

        if nom_source not in OFFER_SOURCE_NAMES:
            invalides += 1
            continue

        titre = nettoyer_texte(ligne_preparee.get("title"))
        description = nettoyer_texte(ligne_preparee.get("description"))
        if not titre and not description:
            invalides += 1
            continue

        est_pertinente, score_perimetre, raisons = evaluer_perimetre_metier(
            ligne_preparee
        )
        if not est_pertinente:
            hors_perimetre += 1
            continue

        ligne_preparee["record_kind"] = "offer"
        ligne_preparee["scope_score"] = score_perimetre
        ligne_preparee["scope_reasons"] = raisons
        ligne_preparee["filter_status"] = "kept_offer"
        lignes_filtrees.append(ligne_preparee)

    print(
        f"Nettoyage filtre {nom_source}: "
        f"{len(lignes_filtrees)} conservee(s), "
        f"{invalides} invalide(s), "
        f"{hors_perimetre} hors perimetre."
    )
    return lignes_filtrees


def filtrer_payloads_collectes(
    payloads_par_source: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Filtrer l'ensemble des sorties brutes de collecte."""

    payloads_filtres: dict[str, list[dict[str, Any]]] = {}

    for nom_source, lignes_brutes in payloads_par_source.items():
        payloads_filtres[nom_source] = filtrer_lignes_source(
            nom_source=nom_source,
            lignes_brutes=lignes_brutes,
        )

    return payloads_filtres
