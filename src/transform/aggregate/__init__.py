"""Aggregation-stage helpers for the transformation pipeline.

This package is responsible for the final orchestration of the transformation
stage after source-specific collection has already finished.
"""

from .aggregate import construire_dataset_final_agrege

__all__ = ["construire_dataset_final_agrege"]
