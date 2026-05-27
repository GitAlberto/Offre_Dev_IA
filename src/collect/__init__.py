"""Public entry points for the collection orchestration layer.

This package is the bridge between:
- source-specific collection functions in `src/collect/fonctions/`;
- the raw collected payloads saved in `data/raw/`;
- the downstream transformation stage in `src/transform/`.

The main callable exposed here is `collecter_toutes_les_sources()`.
"""

from .collect import collecter_toutes_les_sources, sauvegarder_collecte_brute

__all__ = [
    "collecter_toutes_les_sources",
    "sauvegarder_collecte_brute",
]
