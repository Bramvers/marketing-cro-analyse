"""Smoke tests for the Streamlit pages."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
PAGES = sorted((ROOT / "pages").glob("*.py"))


def test_app_entry_runs():
    at = AppTest.from_file(str(ROOT / "app.py")).run()
    assert not at.exception


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.stem)
def test_page_runs(page):
    at = AppTest.from_file(str(page)).run()
    assert not at.exception


def test_overview_loads_dummy_data_without_errors():
    at = AppTest.from_file(str(ROOT / "pages" / "overzicht.py")).run()
    at.button[0].click().run()
    assert not at.exception
    assert len(at.success) == 4
    assert not at.error
