"""Shared import pipeline pieces used by more than one feature module.

``parsing`` owns file, encoding, limit, and safe-XLSX handling; ``header`` owns
generic header-row detection and column mapping. Neither imports a feature
module's code or column registry.
"""
