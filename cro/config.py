"""Load and validate `config/funnel.yaml`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, model_validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "funnel.yaml"


class Option(BaseModel):
    id: str
    label: str


class FunnelStep(Option):
    ga4_event: str
    landing_page_only: bool = False


class ProductLine(Option):
    landing_page_regex: str
    enabled: bool = False


class Funnel(BaseModel):
    counting_unit: Literal["users", "sessions"]
    funnel_type: Literal["open", "closed"]
    steps: list[FunnelStep]
    micro_conversion: str
    macro_conversion: str

    @model_validator(mode="after")
    def _conversions_are_steps(self) -> Funnel:
        ids = self.step_ids
        if len(set(ids)) != len(ids):
            raise ValueError("Funnel step ids must be unique")
        for name in ("micro_conversion", "macro_conversion"):
            if getattr(self, name) not in ids:
                raise ValueError(f"{name} '{getattr(self, name)}' is not a funnel step")
        if ids.index(self.micro_conversion) >= ids.index(self.macro_conversion):
            raise ValueError("micro_conversion must come before macro_conversion")
        return self

    @property
    def step_ids(self) -> list[str]:
        return [s.id for s in self.steps]

    def step_order(self, step_id: str) -> int:
        return self.step_ids.index(step_id)


class Segments(BaseModel):
    device: list[Option]
    channel: list[Option]
    period: Literal["date", "week", "month"]


class Thresholds(BaseModel):
    min_conversions: int
    alpha: float
    power: float
    default_mde_relative: float


class AppConfig(BaseModel):
    funnel: Funnel
    product_lines: list[ProductLine]
    segments: Segments
    thresholds: Thresholds

    @property
    def product_line_ids(self) -> list[str]:
        return [p.id for p in self.product_lines]

    @property
    def device_ids(self) -> list[str]:
        return [d.id for d in self.segments.device]

    @property
    def channel_ids(self) -> list[str]:
        return [c.id for c in self.segments.channel]


def load_config(path: Path | None = None) -> AppConfig:
    """Parse the YAML file at `path` (defaults to config/funnel.yaml) into an AppConfig."""
    path = path or DEFAULT_CONFIG_PATH
    with path.open(encoding="utf-8") as fh:
        return AppConfig.model_validate(yaml.safe_load(fh))


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Cached default config."""
    return load_config()
