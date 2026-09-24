import pandas as pd
import pytest

from cro.config import load_config
from cro.model import Severity, validate

STEPS = ["page_view", "view_item", "add_to_cart", "begin_checkout", "add_payment_info", "purchase"]


def funnel_frame(counts=(1000, 600, 300, 150, 120, 110), date="2026-07-01", device="mobile", channel="sea"):
    return pd.DataFrame(
        {
            "date": [date] * len(STEPS),
            "product_line": ["auto"] * len(STEPS),
            "step": STEPS,
            "device": [device] * len(STEPS),
            "channel": [channel] * len(STEPS),
            "users": [str(c) for c in counts],
        }
    )


def codes(result, severity=None):
    return {i.code for i in result.report.issues if severity is None or i.severity is severity}


def test_valid_funnel_has_no_issues():
    result = validate("funnel_steps", funnel_frame())
    assert result.report.is_valid
    assert result.report.issues == []
    assert str(result.data["users"].dtype) == "Int64"
    assert pd.api.types.is_datetime64_any_dtype(result.data["date"])


def test_missing_required_column_is_error():
    result = validate("funnel_steps", funnel_frame().drop(columns=["users"]))
    assert not result.report.is_valid
    assert codes(result) == {"missing_columns"}
    assert "users" in result.report.errors[0].message


def test_non_numeric_and_negative_counts_are_errors():
    df = funnel_frame()
    df.loc[1, "users"] = "veel"
    df.loc[2, "users"] = "-5"
    df.loc[3, "users"] = "12.5"
    result = validate("funnel_steps", df)
    invalid = next(i for i in result.report.errors if i.code == "invalid_type")
    assert invalid.count == 2 and invalid.rows == [1, 3]
    assert "below_min" in codes(result, Severity.ERROR)


def test_invalid_date_is_error():
    df = funnel_frame()
    df.loc[0, "date"] = "gisteren"
    assert "invalid_type" in codes(validate("funnel_steps", df), Severity.ERROR)


def test_unknown_step_is_error_unknown_channel_is_warning():
    df = funnel_frame()
    df.loc[0, "step"] = "premium_calculated"
    result = validate("funnel_steps", df)
    assert "unknown_value" in codes(result, Severity.ERROR)

    result = validate("funnel_steps", funnel_frame(channel="tiktok"))
    assert result.report.is_valid
    assert "unknown_value" in codes(result, Severity.WARNING)


def test_duplicate_rows_are_error():
    df = pd.concat([funnel_frame(), funnel_frame().iloc[[0]]], ignore_index=True)
    result = validate("funnel_steps", df)
    dup = next(i for i in result.report.errors if i.code == "duplicate_rows")
    assert dup.count == 2


def test_step_increase_is_warning_in_open_funnel():
    result = validate("funnel_steps", funnel_frame(counts=(1000, 600, 700, 150, 120, 110)))
    assert result.report.is_valid
    issue = next(i for i in result.report.warnings if i.code == "step_increase")
    assert "Premie berekend" in issue.message
    assert issue.rows == [2]


def test_step_increase_is_error_in_closed_funnel():
    config = load_config()
    config.funnel.funnel_type = "closed"
    result = validate("funnel_steps", funnel_frame(counts=(1000, 600, 700, 150, 120, 110)), config)
    assert "step_increase" in codes(result, Severity.ERROR)


def test_missing_steps_are_warned():
    df = funnel_frame().iloc[:-1]
    assert "absent_steps" in codes(validate("funnel_steps", df), Severity.WARNING)


def test_small_sample_is_warned_per_segment():
    big = funnel_frame(counts=(10000, 6000, 3000, 1500, 1200, 1100), device="desktop", channel="seo")
    small = funnel_frame(counts=(100, 60, 30, 15, 12, 11), device="tablet", channel="seo")
    result = validate("funnel_steps", pd.concat([big, small], ignore_index=True))
    messages = [i.message for i in result.report.warnings if i.code == "small_sample"]
    assert len(messages) == 1
    assert "tablet" in messages[0]


def test_experiment_checks():
    df = pd.DataFrame(
        {
            "experiment_id": ["E1", "E1"],
            "name": ["Test", "Test"],
            "product_line": ["auto", "auto"],
            "variant": ["a", "b"],
            "is_control": ["ja", "ja"],
            "metric": ["add_to_cart", "add_to_cart"],
            "visitors": ["1000", "1000"],
            "conversions": ["200", "1200"],
            "start_date": ["2026-07-01", "2026-07-01"],
            "end_date": ["2026-07-20", "2026-06-01"],
            "status": ["concluded", "finished"],
        }
    )
    errors = codes(validate("experiments", df), Severity.ERROR)
    assert {"conversions_gt_visitors", "control_count", "period_reversed", "unknown_value"} <= errors


def test_zone_rates_must_be_between_0_and_1():
    df = pd.DataFrame(
        {
            "period_start": ["2026-07-01"],
            "period_end": ["2026-07-31"],
            "product_line": ["auto"],
            "page": ["/verzekeringen/autoverzekering"],
            "zone": ["cta"],
            "device": ["mobile"],
            "exposure_rate": ["45"],  # percentage instead of fraction
            "click_rate": ["0.2"],
        }
    )
    assert "above_max" in codes(validate("cs_zones", df), Severity.ERROR)


def test_notes_pillar_must_be_known():
    df = pd.DataFrame(
        {
            "note_id": ["Q1"],
            "date": ["2026-07-01"],
            "product_line": ["auto"],
            "pillar": ["onderbuik"],
            "source": ["usertest"],
            "observation": ["Iets gezien"],
        }
    )
    assert "unknown_value" in codes(validate("qual_notes", df), Severity.ERROR)


@pytest.mark.parametrize("table", ["funnel_steps", "cs_zones", "experiments", "qual_notes"])
def test_empty_table_is_error(table):
    from cro.model import ALL_SCHEMAS

    df = pd.DataFrame(columns=ALL_SCHEMAS[table].column_names)
    assert "empty_table" in codes(validate(table, df), Severity.ERROR)
