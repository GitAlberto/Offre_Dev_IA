"""Orchestrateur final de la transformation et de l'agregation.

Ce module est l'endroit ou l'on assemble la phase C3 dans son ensemble.

Ce qu'il est cense faire :
- recevoir les donnees brutes issues de la collecte multi-sources ;
- appeler `etape_1_filtrage.py` pour filtrer et preparer les lignes ;
- appeler `etape_2_normalisation.py` pour harmoniser les formats ;
- appeler `etape_3_deduplication.py` pour retirer les doublons sur les offres ;
- produire la structure finale qui sera ensuite exportee en CSV ou importee en
  base.

Ce qui est cense l'appeler :
- `src/pipeline.py` dans le flux complet ;
- ou un futur script de test d'integration de la phase de transformation.

Ce que ce module n'est pas cense faire :
- interroger directement les sources de collecte ;
- porter toute la logique detaillee de nettoyage source par source ;
- faire l'import SQL lui-meme.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..nettoyage.etape_1_filtrage import filtrer_payloads_collectes
from ..nettoyage.etape_2_normalisation import normaliser_payloads_filtres
from ..nettoyage.etape_3_deduplication import dedoublonner_offres_normalisees


DEFAULT_PROCESSED_OUTPUT_PATH = Path("data/processed/clean_dataset.csv")

OFFER_SOURCE_NAMES = {
    "bpce",
    "france_travail",
    "la_bonne_alternance",
    "region_ile_de_france",
    "welcome_to_the_jungle",
    "postgresql_history",
}


def aplatir_sources_offres(
    payloads_normalises_par_source: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Rassembler uniquement les lignes qui correspondent a des offres.

    Pourquoi cette fonction existe :
    - toutes les sources ne representent pas le meme objet metier ;
    - `collect_aggregates_hive` renvoie des agregats ;
    - seules certaines sources doivent alimenter le dataset final des offres.

    Cette fonction est censee etre appelee par
    `construire_dataset_final_agrege()`.
    """

    offres_aplaties: list[dict[str, Any]] = []

    for nom_source, lignes_normalisees in payloads_normalises_par_source.items():
        if nom_source not in OFFER_SOURCE_NAMES:
            continue

        for ligne in lignes_normalisees:
            offre_preparee = dict(ligne)
            offre_preparee.setdefault("source", nom_source)
            offres_aplaties.append(offre_preparee)

    return offres_aplaties


def get_processed_output_path(
    output_path: Path = DEFAULT_PROCESSED_OUTPUT_PATH,
) -> Path:
    """Retourner l'emplacement cible du dataset final nettoye.

    Cette fonction n'ecrit rien sur disque a ce stade.
    Son but est de documenter clairement la destination attendue de la sortie
    finale de transformation.
    """

    return output_path


def construire_dataset_final_agrege(
    payloads_collectes_par_source: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Construire le dataset final agrege a partir des donnees collecteess.

    Ordre d'appel prevu :
    1. `filtrer_payloads_collectes()`
    2. `normaliser_payloads_filtres()`
    3. `aplatir_sources_offres()`
    4. `dedoublonner_offres_normalisees()`

    Ce que cette fonction renvoie :
    - une liste d'offres consolidees en memoire ;
    - prete a etre exportee plus tard en `clean_dataset.csv`.
    """

    payloads_filtres = filtrer_payloads_collectes(
        payloads_par_source=payloads_collectes_par_source,
    )
    payloads_normalises = normaliser_payloads_filtres(
        payloads_filtres_par_source=payloads_filtres,
    )
    offres_aplaties = aplatir_sources_offres(
        payloads_normalises_par_source=payloads_normalises,
    )
    offres_finales = dedoublonner_offres_normalisees(
        offres_normalisees=offres_aplaties,
    )

    # On calcule l'emplacement final meme si l'ecriture disque n'est pas encore
    # implemente. Cela permet de figer la convention de sortie des maintenant.
    _ = get_processed_output_path()

    return offres_finales
