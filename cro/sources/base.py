"""Source interface: one implementation per origin (CSV now, API later).

A source knows how to fetch raw data and translate it into one normalized table
(see `cro.model.schemas`). Validation happens afterwards, independent of the source,
so a CSV loader can later be swapped for an API loader without touching the analysis.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from cro.config import AppConfig
from cro.model import ALL_SCHEMAS, TableSchema, ValidationResult, validate


class Source(ABC):
    """Produces one normalized table."""

    #: Name of the normalized table this source produces (key of `ALL_SCHEMAS`).
    table: str

    @property
    def schema(self) -> TableSchema:
        return ALL_SCHEMAS[self.table]

    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Return the data with columns named after the normalized schema (not yet validated)."""

    def load_validated(self, config: AppConfig | None = None) -> ValidationResult:
        return validate(self.table, self.load(), config)
