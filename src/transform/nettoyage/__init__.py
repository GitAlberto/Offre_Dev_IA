"""Cleaning-stage helpers for raw collected payloads.

This package contains the cleaning steps that happen before final aggregation:
- filtering invalid rows;
- normalizing heterogeneous formats;
- deduplicating comparable offers.
"""

from .etape_1_filtrage import filtrer_payloads_collectes
from .etape_2_normalisation import normaliser_payloads_filtres
from .etape_3_deduplication import dedoublonner_offres_normalisees

__all__ = [
    "dedoublonner_offres_normalisees",
    "filtrer_payloads_collectes",
    "normaliser_payloads_filtres",
]
