"""Shared Streamlit helpers (Dutch UI texts)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from cro.config import PROJECT_ROOT
from cro.model import ALL_SCHEMAS, ValidationReport, ValidationResult
from cro.sources import CsvSource

DUMMY_DIR = PROJECT_ROOT / "data" / "dummy"
DATASETS_KEY = "datasets"


def datasets() -> dict[str, ValidationResult]:
    """Validated tables loaded in this session, keyed by table name."""
    return st.session_state.setdefault(DATASETS_KEY, {})


def load_dummy_data(directory: Path = DUMMY_DIR) -> None:
    loaded = datasets()
    for table in ALL_SCHEMAS:
        path = directory / f"{table}.csv"
        if path.exists():
            loaded[table] = CsvSource(table, path).load_validated()


def render_report(report: ValidationReport) -> None:
    label = ALL_SCHEMAS[report.table].label
    if report.is_valid and not report.warnings:
        st.success(f"**{label}** — {report.n_rows} rijen, geen problemen gevonden.")
    elif report.is_valid:
        st.warning(f"**{label}** — {report.n_rows} rijen, {len(report.warnings)} waarschuwing(en).")
    else:
        st.error(f"**{label}** — {len(report.errors)} fout(en); de tabel kan niet worden gebruikt.")
    for issue in report.issues:
        rows = f" Voorbeeldrijen: {', '.join(str(r + 2) for r in issue.rows)}." if issue.rows else ""
        icon = "❌" if issue.severity == "error" else "⚠️"
        st.markdown(f"{icon} {issue.message}{rows}")
