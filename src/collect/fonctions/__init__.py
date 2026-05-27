"""Public entry points for source-specific collection functions.

This package is meant to be imported by the future collection orchestrator
located in `src/collect/collect.py`.

Naming convention used in this package:
- `collect_offres_*` for sources that primarily return job offers;
- `collect_reference_*` for reference data sources;
- `collect_aggregates_*` for aggregate-oriented analytical sources.
"""

from .collect_aggregates_hive import collect_aggregates_hive
from .collect_offres_france_travail import collect_offres_france_travail
from .collect_offres_postgresql_history import collect_offres_postgresql_history
from .collect_offres_welcome_to_the_jungle import (
    collect_offres_welcome_to_the_jungle,
)
from .collect_reference_rome import collect_reference_rome

__all__ = [
    "collect_aggregates_hive",
    "collect_offres_france_travail",
    "collect_offres_postgresql_history",
    "collect_offres_welcome_to_the_jungle",
    "collect_reference_rome",
]
