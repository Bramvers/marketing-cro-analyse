"""CSV-backed sources."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pandas as pd

from cro.model import ALL_SCHEMAS
from cro.sources.base import Source


class CsvSource(Source):
    """Reads a CSV export and renames its columns to the normalized schema.

    `column_mapping` maps export column names to schema column names. Source-specific
    mappings (GA4, Contentsquare, Optimizely export formats) are added in phase 2.
    """

    def __init__(
        self,
        table: str,
        file: Path | str | BinaryIO,
        column_mapping: dict[str, str] | None = None,
    ) -> None:
        if table not in ALL_SCHEMAS:
            raise ValueError(f"Unknown table '{table}'. Expected one of: {', '.join(ALL_SCHEMAS)}")
        self.table = table
        self.file = file
        self.column_mapping = column_mapping or {}

    def load(self) -> pd.DataFrame:
        # Read everything as text; type coercion is part of validation so bad values get reported, not dropped.
        df = pd.read_csv(self.file, dtype=str, keep_default_na=False, sep=None, engine="python", encoding="utf-8-sig")
        df.columns = [str(c).strip() for c in df.columns]
        return df.rename(columns=self.column_mapping)
