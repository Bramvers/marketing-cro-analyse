"""The dummy data must validate cleanly and contain the built-in patterns."""

from pathlib import Path

import pandas as pd
import pytest

from cro import dummy
from cro.model import validate
from cro.sources import CsvSource


@pytest.fixture(scope="module")
def data():
    return dummy.generate_all()


def test_generation_is_deterministic(data):
    again = dummy.generate_funnel_steps()
    pd.testing.assert_frame_equal(data["funnel_steps"], again)


@pytest.mark.parametrize("table", ["funnel_steps", "cs_zones", "experiments", "qual_notes"])
def test_dummy_validates_without_issues(data, tmp_path, table):
    path = tmp_path / f"{table}.csv"
    data[table].to_csv(path, index=False)
    report = CsvSource(table, path).load_validated().report
    assert report.is_valid, [i.message for i in report.errors]
    assert report.warnings == []


def _rate(df, num_step, den_step, by):
    wide = df.pivot_table(index=by, columns="step", values="users", aggfunc="sum")
    return wide[num_step] / wide[den_step]


def test_pattern_mobile_landing_drop(data):
    rate = _rate(data["funnel_steps"], "view_item", "page_view", "device")
    assert rate["mobile"] / rate["desktop"] == pytest.approx(dummy.MOBILE_LANDING_DROP["multiplier"], abs=0.02)


def test_pattern_sea_premium_gap(data):
    rate = _rate(data["funnel_steps"], "add_to_cart", "view_item", "channel")
    assert rate["sea"] / rate["seo"] == pytest.approx(dummy.SEA_PREMIUM_GAP["multiplier"], abs=0.03)


def test_pattern_payment_dip(data):
    df = data["funnel_steps"].copy()
    dip = dummy.PAYMENT_DIP
    df["in_dip"] = (df["date"] >= dip["start"]) & (df["date"] <= dip["end"])
    rate = _rate(df, "add_payment_info", "begin_checkout", "in_dip")
    assert rate[True] / rate[False] == pytest.approx(dip["multiplier"], abs=0.03)


def test_committed_dummy_csvs_are_valid():
    for table in ("funnel_steps", "cs_zones", "experiments", "qual_notes"):
        path = Path(__file__).resolve().parent.parent / "data" / "dummy" / f"{table}.csv"
        assert validate(table, CsvSource(table, path).load()).report.is_valid
