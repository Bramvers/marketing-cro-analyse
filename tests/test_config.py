import pytest
import yaml
from pydantic import ValidationError

from cro.config import DEFAULT_CONFIG_PATH, AppConfig, load_config


def test_default_config_loads():
    config = load_config()
    assert config.funnel.step_ids == [
        "page_view",
        "view_item",
        "add_to_cart",
        "begin_checkout",
        "add_payment_info",
        "purchase",
    ]
    assert config.funnel.micro_conversion == "add_to_cart"
    assert config.funnel.macro_conversion == "purchase"
    assert config.funnel.counting_unit == "users"
    assert config.funnel.funnel_type == "open"
    assert config.segments.period == "date"
    assert set(config.product_line_ids) == {"auto", "woon", "reis", "fiets", "bromfiets"}


def _raw():
    with DEFAULT_CONFIG_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_micro_conversion_must_be_a_step():
    raw = _raw()
    raw["funnel"]["micro_conversion"] = "premium_calculated"
    with pytest.raises(ValidationError, match="not a funnel step"):
        AppConfig.model_validate(raw)


def test_micro_must_precede_macro():
    raw = _raw()
    raw["funnel"]["micro_conversion"], raw["funnel"]["macro_conversion"] = "purchase", "add_to_cart"
    with pytest.raises(ValidationError, match="before"):
        AppConfig.model_validate(raw)
