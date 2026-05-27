"""Top-level helpers for the transformation stage.

This package sits between raw collection and database import.

Expected high-level call chain:
- `src/pipeline.py` launches the full workflow;
- `src/collect/collect.py` returns raw collected payloads;
- `src/transform/aggregate/aggregate.py` orchestrates the transformation stage;
- the nettoyage subpackage performs filtering, normalization and deduplication.
"""

from .aggregate.aggregate import construire_dataset_final_agrege
from .nettoyage.etape_1_filtrage import filtrer_payloads_collectes
from .nettoyage.etape_2_normalisation import normaliser_payloads_filtres
from .nettoyage.etape_3_deduplication import dedoublonner_offres_normalisees

__all__ = [
    "construire_dataset_final_agrege",
    "dedoublonner_offres_normalisees",
    "filtrer_payloads_collectes",
    "normaliser_payloads_filtres",
]
