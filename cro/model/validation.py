"""Validation of normalized tables.

Every check yields `ValidationIssue`s with a Dutch message for the UI. Errors make a table
unusable; warnings are shown but do not block analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import pandas as pd
from pydantic import BaseModel

from cro.config import AppConfig, get_config
from cro.model.schemas import CS_ZONES, EXPERIMENTS, FUNNEL_STEPS, QUAL_NOTES, TableSchema

MAX_ROW_SAMPLES = 10
_TRUE = {"true", "1", "yes", "ja", "y", "t"}
_FALSE = {"false", "0", "no", "nee", "n", "f"}


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ValidationIssue(BaseModel):
    severity: Severity
    table: str
    code: str
    message: str
    column: str | None = None
    count: int = 0
    rows: list[int] = []  # sample of offending 0-based row positions


class ValidationReport(BaseModel):
    table: str
    n_rows: int
    issues: list[ValidationIssue] = []

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]

    @property
    def is_valid(self) -> bool:
        return not self.errors


@dataclass
class ValidationResult:
    data: pd.DataFrame  # coerced to the schema's types; only meaningful when report.is_valid
    report: ValidationReport


class _Collector:
    def __init__(self, table: str) -> None:
        self.table = table
        self.issues: list[ValidationIssue] = []

    def add(
        self,
        severity: Severity,
        code: str,
        message: str,
        column: str | None = None,
        mask: pd.Series | None = None,
    ) -> None:
        rows: list[int] = []
        count = 0
        if mask is not None:
            positions = np.flatnonzero(mask.to_numpy())
            count = len(positions)
            rows = positions[:MAX_ROW_SAMPLES].tolist()
        self.issues.append(
            ValidationIssue(
                severity=severity, table=self.table, code=code, message=message, column=column, count=count, rows=rows
            )
        )


def _coerce_column(series: pd.Series, kind: str) -> tuple[pd.Series, pd.Series]:
    """Return (coerced series, mask of values that could not be coerced)."""
    present = series.notna() & (series.astype("string").str.strip() != "")
    if kind == "date":
        coerced = pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=False).dt.normalize()
    elif kind == "int":
        numeric = pd.to_numeric(series, errors="coerce")
        not_whole = numeric.notna() & (numeric % 1 != 0)
        numeric = numeric.mask(not_whole)
        coerced = numeric.astype("Int64")
    elif kind == "float":
        coerced = pd.to_numeric(series, errors="coerce").astype("Float64")
    elif kind == "bool":
        text = series.astype("string").str.strip().str.lower()
        coerced = pd.Series(pd.NA, index=series.index, dtype="boolean")
        coerced[text.isin(_TRUE)] = True
        coerced[text.isin(_FALSE)] = False
    else:
        coerced = series.astype("string").str.strip()
        coerced = coerced.mask(coerced == "")
    bad = present & coerced.isna()
    return coerced, bad


def _validate_structure(df: pd.DataFrame, schema: TableSchema, col: _Collector) -> pd.DataFrame | None:
    """Generic checks shared by all tables. Returns the coerced frame, or None if columns are missing."""
    missing = [c for c in schema.required_columns if c not in df.columns]
    if missing:
        col.add(
            Severity.ERROR,
            "missing_columns",
            f"Verplichte kolommen ontbreken: {', '.join(missing)}.",
        )
        return None

    unknown = [c for c in df.columns if c not in schema.column_names]
    if unknown:
        col.add(Severity.WARNING, "unknown_columns", f"Onbekende kolommen worden genegeerd: {', '.join(map(str, unknown))}.")

    if df.empty:
        col.add(Severity.ERROR, "empty_table", "De tabel bevat geen rijen.")

    out = pd.DataFrame(index=df.index)
    for spec in schema.columns:
        if spec.name not in df.columns:
            continue
        coerced, bad = _coerce_column(df[spec.name], spec.kind)
        out[spec.name] = coerced
        if bad.any():
            col.add(
                Severity.ERROR,
                "invalid_type",
                f"Kolom '{spec.name}' bevat {int(bad.sum())} waarde(n) die geen geldige {_KIND_NL[spec.kind]} zijn.",
                spec.name,
                bad,
            )
        if spec.required:
            empty = coerced.isna() & ~bad
            if empty.any():
                col.add(
                    Severity.ERROR,
                    "missing_values",
                    f"Kolom '{spec.name}' is verplicht maar heeft {int(empty.sum())} lege waarde(n).",
                    spec.name,
                    empty,
                )
        if spec.min is not None:
            below = (coerced < spec.min).fillna(False).astype(bool)
            if below.any():
                col.add(
                    Severity.ERROR,
                    "below_min",
                    f"Kolom '{spec.name}' heeft {int(below.sum())} waarde(n) kleiner dan {spec.min:g}.",
                    spec.name,
                    below,
                )
        if spec.max is not None:
            above = (coerced > spec.max).fillna(False).astype(bool)
            if above.any():
                col.add(
                    Severity.ERROR,
                    "above_max",
                    f"Kolom '{spec.name}' heeft {int(above.sum())} waarde(n) groter dan {spec.max:g}.",
                    spec.name,
                    above,
                )
        if spec.allowed is not None:
            _check_allowed(coerced, spec.name, spec.allowed, Severity.ERROR, col)

    key_cols = [k for k in schema.key if k in out.columns]
    if key_cols:
        dup = out.duplicated(subset=key_cols, keep=False)
        if dup.any():
            col.add(
                Severity.ERROR,
                "duplicate_rows",
                f"{int(dup.sum())} rijen hebben dezelfde combinatie van {', '.join(key_cols)}.",
                mask=dup,
            )
    return out


_KIND_NL = {"date": "datum", "int": "geheel getal", "float": "getal", "str": "tekst", "bool": "ja/nee-waarde"}


def _check_allowed(
    values: pd.Series, column: str, allowed: list[str], severity: Severity, col: _Collector
) -> None:
    bad = values.notna() & ~values.isin(allowed)
    if bad.any():
        examples = ", ".join(sorted(map(str, values[bad].unique()))[:5])
        col.add(
            severity,
            "unknown_value",
            f"Kolom '{column}' bevat onbekende waarden ({examples}). Toegestaan: {', '.join(allowed)}.",
            column,
            bad,
        )


def _finish(df: pd.DataFrame, out: pd.DataFrame | None, schema: TableSchema, col: _Collector) -> ValidationResult:
    report = ValidationReport(table=schema.name, n_rows=len(df), issues=col.issues)
    return ValidationResult(data=out if out is not None else df, report=report)


# --- Table-specific validators -------------------------------------------------------------


def validate_funnel_steps(df: pd.DataFrame, config: AppConfig | None = None) -> ValidationResult:
    config = config or get_config()
    col = _Collector(FUNNEL_STEPS.name)
    out = _validate_structure(df, FUNNEL_STEPS, col)
    if out is None or not len(out):
        return _finish(df, out, FUNNEL_STEPS, col)

    funnel = config.funnel
    _check_allowed(out["product_line"], "product_line", config.product_line_ids, Severity.ERROR, col)
    _check_allowed(out["step"], "step", funnel.step_ids, Severity.ERROR, col)
    _check_allowed(out["device"], "device", config.device_ids, Severity.WARNING, col)
    _check_allowed(out["channel"], "channel", config.channel_ids, Severity.WARNING, col)

    if col.issues and any(i.severity is Severity.ERROR for i in col.issues):
        return _finish(df, out, FUNNEL_STEPS, col)

    _check_step_order(out, config, col)
    _check_missing_steps(out, config, col)
    _check_funnel_sample_size(out, config, col)
    return _finish(df, out, FUNNEL_STEPS, col)


def _funnel_wide(out: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """One row per (date, product_line, device, channel), one column per step (in funnel order)."""
    wide = out.pivot_table(
        index=["date", "product_line", "device", "channel"],
        columns="step",
        values="users",
        aggfunc="sum",
        observed=True,
    )
    return wide.reindex(columns=[s for s in config.funnel.step_ids if s in wide.columns])


def _check_step_order(out: pd.DataFrame, config: AppConfig, col: _Collector) -> None:
    """Step N > step N-1 is illogical in a closed funnel and suspicious in an open one."""
    wide = _funnel_wide(out, config)
    steps = list(wide.columns)
    labels = {s.id: s.label for s in config.funnel.steps}
    severity = Severity.ERROR if config.funnel.funnel_type == "closed" else Severity.WARNING
    for prev, curr in zip(steps, steps[1:]):
        increase = (wide[curr] > wide[prev]).fillna(False).astype(bool)
        if not increase.any():
            continue
        n = int(increase.sum())
        pct = n / len(wide)
        reason = (
            "Dat kan in een open funnel (instap halverwege), maar controleer de tracking."
            if severity is Severity.WARNING
            else "In een gesloten funnel is dat onmogelijk."
        )
        row_keys = pd.MultiIndex.from_frame(out[list(wide.index.names)])
        mask = pd.Series(row_keys.isin(wide.index[increase]), index=out.index) & (out["step"] == curr)
        col.add(
            severity,
            "step_increase",
            f"Stap '{labels[curr]}' heeft meer gebruikers dan '{labels[prev]}' in {n} combinaties "
            f"van datum/segment ({pct:.1%}). {reason}",
            "users",
            mask,
        )


def _check_missing_steps(out: pd.DataFrame, config: AppConfig, col: _Collector) -> None:
    wide = _funnel_wide(out, config)
    absent = [s.label for s in config.funnel.steps if s.id not in wide.columns]
    if absent:
        col.add(Severity.WARNING, "absent_steps", f"Deze funnelstappen komen niet voor in de data: {', '.join(absent)}.")
    partial = wide.isna().any(axis=1)
    if partial.any():
        col.add(
            Severity.WARNING,
            "incomplete_segments",
            f"{int(partial.sum())} combinaties van datum/segment missen één of meer funnelstappen.",
        )


def _check_funnel_sample_size(out: pd.DataFrame, config: AppConfig, col: _Collector) -> None:
    """Warn per segment value when macro-conversions over the whole period are below the threshold."""
    threshold = config.thresholds.min_conversions
    macro = out[out["step"] == config.funnel.macro_conversion]
    macro_label = next(s.label for s in config.funnel.steps if s.id == config.funnel.macro_conversion)
    for dim, dim_nl in (("device", "apparaat"), ("channel", "kanaal")):
        totals = macro.groupby(["product_line", dim], observed=True)["users"].sum()
        small = totals[totals < threshold]
        for (product_line, value), n in small.items():
            col.add(
                Severity.WARNING,
                "small_sample",
                f"Klein sample: {dim_nl} '{value}' ({product_line}) heeft {int(n)} × '{macro_label}' "
                f"(drempel {threshold}). Conclusies voor dit segment zijn onbetrouwbaar.",
                dim,
            )


def validate_cs_zones(df: pd.DataFrame, config: AppConfig | None = None) -> ValidationResult:
    config = config or get_config()
    col = _Collector(CS_ZONES.name)
    out = _validate_structure(df, CS_ZONES, col)
    if out is None or not len(out):
        return _finish(df, out, CS_ZONES, col)

    _check_allowed(out["product_line"], "product_line", config.product_line_ids, Severity.ERROR, col)
    _check_allowed(out["device"], "device", config.device_ids, Severity.WARNING, col)
    reversed_period = (out["period_end"] < out["period_start"]).fillna(False).astype(bool)
    if reversed_period.any():
        col.add(Severity.ERROR, "period_reversed", "Einddatum ligt vóór de begindatum.", "period_end", reversed_period)
    clicks_gt_exposure = (out["click_rate"] > out["exposure_rate"]).fillna(False).astype(bool)
    if clicks_gt_exposure.any():
        col.add(
            Severity.WARNING,
            "click_gt_exposure",
            "Click rate is hoger dan exposure rate; controleer of de export dezelfde noemer gebruikt.",
            "click_rate",
            clicks_gt_exposure,
        )
    if "pageviews" in out.columns:
        small = (out["pageviews"] < config.thresholds.min_conversions).fillna(False).astype(bool)
        if small.any():
            col.add(
                Severity.WARNING,
                "small_sample",
                f"{int(small.sum())} zone(s) hebben minder dan {config.thresholds.min_conversions} pageviews.",
                "pageviews",
                small,
            )
    return _finish(df, out, CS_ZONES, col)


def validate_experiments(df: pd.DataFrame, config: AppConfig | None = None) -> ValidationResult:
    config = config or get_config()
    col = _Collector(EXPERIMENTS.name)
    out = _validate_structure(df, EXPERIMENTS, col)
    if out is None or not len(out):
        return _finish(df, out, EXPERIMENTS, col)

    _check_allowed(out["product_line"], "product_line", config.product_line_ids, Severity.ERROR, col)
    too_many = (out["conversions"] > out["visitors"]).fillna(False).astype(bool)
    if too_many.any():
        col.add(Severity.ERROR, "conversions_gt_visitors", "Meer conversies dan bezoekers.", "conversions", too_many)
    if "end_date" in out.columns:
        reversed_period = (out["end_date"] < out["start_date"]).fillna(False).astype(bool)
        if reversed_period.any():
            col.add(Severity.ERROR, "period_reversed", "Einddatum ligt vóór de startdatum.", "end_date", reversed_period)

    controls = out.groupby(["experiment_id", "metric"], observed=True)["is_control"].sum()
    for (exp_id, metric), n in controls[controls != 1].items():
        col.add(
            Severity.ERROR,
            "control_count",
            f"Experiment '{exp_id}' / metric '{metric}' heeft {int(n)} controlevarianten; precies 1 verwacht.",
            "is_control",
        )

    small = (out["conversions"] < config.thresholds.min_conversions).fillna(False).astype(bool)
    if small.any():
        col.add(
            Severity.WARNING,
            "small_sample",
            f"{int(small.sum())} variant(en) hebben minder dan {config.thresholds.min_conversions} conversies.",
            "conversions",
            small,
        )
    return _finish(df, out, EXPERIMENTS, col)


def validate_qual_notes(df: pd.DataFrame, config: AppConfig | None = None) -> ValidationResult:
    config = config or get_config()
    col = _Collector(QUAL_NOTES.name)
    out = _validate_structure(df, QUAL_NOTES, col)
    if out is None or not len(out):
        return _finish(df, out, QUAL_NOTES, col)

    _check_allowed(out["product_line"], "product_line", config.product_line_ids, Severity.ERROR, col)
    if "step" in out.columns:
        _check_allowed(out["step"], "step", config.funnel.step_ids, Severity.WARNING, col)
    return _finish(df, out, QUAL_NOTES, col)


VALIDATORS = {
    FUNNEL_STEPS.name: validate_funnel_steps,
    CS_ZONES.name: validate_cs_zones,
    EXPERIMENTS.name: validate_experiments,
    QUAL_NOTES.name: validate_qual_notes,
}


def validate(table: str, df: pd.DataFrame, config: AppConfig | None = None) -> ValidationResult:
    """Validate `df` as the normalized table named `table`."""
    return VALIDATORS[table](df, config)
