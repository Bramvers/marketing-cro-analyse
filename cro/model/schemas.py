"""Normalized data model: every source is translated into one of these tables.

Tables are pandas DataFrames; their shape is described by a `TableSchema` so that
validation (see `validation.py`) can check any source against the same contract.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ColumnKind = Literal["date", "int", "float", "str", "bool"]


class ColumnSpec(BaseModel):
    name: str
    kind: ColumnKind
    required: bool = True
    min: float | None = None
    max: float | None = None
    allowed: list[str] | None = None
    description: str = ""


class TableSchema(BaseModel):
    name: str
    label: str  # Dutch, shown in the UI
    columns: list[ColumnSpec]
    key: list[str]  # columns that must be unique together

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    @property
    def required_columns(self) -> list[str]:
        return [c.name for c in self.columns if c.required]


FUNNEL_STEPS = TableSchema(
    name="funnel_steps",
    label="Funnelstappen (GA4 / BigQuery)",
    key=["date", "product_line", "step", "device", "channel"],
    columns=[
        ColumnSpec(name="date", kind="date", description="Datum"),
        ColumnSpec(name="product_line", kind="str", description="Productlijn-id uit funnel.yaml"),
        ColumnSpec(name="step", kind="str", description="Funnelstap-id uit funnel.yaml"),
        ColumnSpec(name="device", kind="str", description="Apparaattype"),
        ColumnSpec(name="channel", kind="str", description="Kanaal"),
        ColumnSpec(name="users", kind="int", min=0, description="Aantal gebruikers dat de stap bereikte"),
        ColumnSpec(name="source", kind="str", required=False, description="Herkomst (ga4, bigquery, screenshot, dummy)"),
    ],
)

CS_ZONES = TableSchema(
    name="cs_zones",
    label="Contentsquare-zones",
    key=["period_start", "period_end", "product_line", "page", "zone", "device"],
    columns=[
        ColumnSpec(name="period_start", kind="date", description="Begin periode"),
        ColumnSpec(name="period_end", kind="date", description="Einde periode"),
        ColumnSpec(name="product_line", kind="str", description="Productlijn-id"),
        ColumnSpec(name="page", kind="str", description="Pagina (pad of naam)"),
        ColumnSpec(name="zone", kind="str", description="Zone-naam"),
        ColumnSpec(name="device", kind="str", description="Apparaattype"),
        ColumnSpec(name="exposure_rate", kind="float", min=0, max=1, description="Aandeel pageviews waarin de zone zichtbaar was"),
        ColumnSpec(name="click_rate", kind="float", min=0, max=1, description="Aandeel pageviews met klik op de zone"),
        ColumnSpec(name="hover_rate", kind="float", min=0, max=1, required=False, description="Aandeel pageviews met hover"),
        ColumnSpec(name="conversion_rate_after_click", kind="float", min=0, max=1, required=False, description="Conversie na klik"),
        ColumnSpec(name="attractiveness_rate", kind="float", min=0, max=1, required=False, description="Klikken als aandeel van exposure"),
        ColumnSpec(name="rage_clicks", kind="int", min=0, required=False, description="Aantal rage clicks"),
        ColumnSpec(name="pageviews", kind="int", min=0, required=False, description="Pageviews in de periode (voor sample-controle)"),
    ],
)

EXPERIMENTS = TableSchema(
    name="experiments",
    label="Optimizely-experimenten",
    key=["experiment_id", "variant", "metric"],
    columns=[
        ColumnSpec(name="experiment_id", kind="str", description="Experiment-id"),
        ColumnSpec(name="name", kind="str", description="Naam van het experiment"),
        ColumnSpec(name="product_line", kind="str", description="Productlijn-id"),
        ColumnSpec(name="variant", kind="str", description="Variantnaam"),
        ColumnSpec(name="is_control", kind="bool", description="Is dit de controlevariant?"),
        ColumnSpec(name="metric", kind="str", description="Metric (bijv. funnelstap-id)"),
        ColumnSpec(name="visitors", kind="int", min=0, description="Bezoekers in de variant"),
        ColumnSpec(name="conversions", kind="int", min=0, description="Conversies in de variant"),
        ColumnSpec(name="start_date", kind="date", description="Startdatum"),
        ColumnSpec(name="end_date", kind="date", required=False, description="Einddatum"),
        ColumnSpec(
            name="status", kind="str", allowed=["running", "concluded", "paused"], description="Status"
        ),
    ],
)

QUAL_NOTES = TableSchema(
    name="qual_notes",
    label="Kwalitatieve notities",
    key=["note_id"],
    columns=[
        ColumnSpec(name="note_id", kind="str", description="Unieke id"),
        ColumnSpec(name="date", kind="date", description="Datum van de observatie"),
        ColumnSpec(name="product_line", kind="str", description="Productlijn-id"),
        ColumnSpec(
            name="pillar",
            kind="str",
            allowed=["sitegedrag", "kwalitatief", "markt"],
            description="CRO-pijler",
        ),
        ColumnSpec(
            name="source",
            kind="str",
            allowed=["usertest", "survey", "sessierecording", "klantenservice", "marktonderzoek"],
            description="Bron van de observatie",
        ),
        ColumnSpec(name="step", kind="str", required=False, description="Funnelstap-id (optioneel)"),
        ColumnSpec(name="segment", kind="str", required=False, description="Segment (optioneel), bijv. device=mobile"),
        ColumnSpec(name="observation", kind="str", description="Observatie"),
        ColumnSpec(name="tags", kind="str", required=False, description="Tags, gescheiden door ';'"),
    ],
)

ALL_SCHEMAS: dict[str, TableSchema] = {s.name: s for s in (FUNNEL_STEPS, CS_ZONES, EXPERIMENTS, QUAL_NOTES)}


class Evidence(BaseModel):
    """A computed, citable fact. Findings and hypotheses must reference one or more evidence ids.

    Produced by `cro.analysis` (phase 3); defined here so the contract is fixed up front.
    """

    evidence_id: str
    type: Literal["metric", "table", "segment", "note", "experiment"]
    description: str
    value: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: float | None = None
    n: int | None = None
    source_table: str
