"""Points d'entree publics pour les fonctions de collecte par source.

Ce package expose les fonctions `collect_*` sans importer toutes les sources
des l'ouverture du package. Cela permet d'isoler les tests d'une source meme
si une autre source est temporairement en panne ou en cours de travail.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


EXPORTS_PAR_MODULE = {
    "collect_aggregates_hive": "collect_aggregates_hive",
    "collect_offres_bpce": "collect_offres_bpce",
    "collect_offres_choisir_service_public": (
        "collect_offres_choisir_service_public"
    ),
    "collect_offres_france_travail": "collect_offres_france_travail",
    "collect_offres_postgresql_history": "collect_offres_postgresql_history",
    "collect_offres_region_ile_de_france": "collect_offres_region_ile_de_france",
    "collect_offres_welcome_to_the_jungle": (
        "collect_offres_welcome_to_the_jungle"
    ),
}

__all__ = list(EXPORTS_PAR_MODULE)


def __getattr__(name: str) -> Any:
    """Importer paresseusement la source demandee uniquement quand il le faut."""

    if name not in EXPORTS_PAR_MODULE:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(f".{EXPORTS_PAR_MODULE[name]}", __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Afficher correctement les symboles publics du package."""

    return sorted(list(globals().keys()) + __all__)
