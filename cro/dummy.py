"""Deterministic dummy data for the Auto funnel, with deliberately built-in patterns.

The patterns below are the "ground truth" that the analysis (phase 3) must rediscover:

1. MOBILE_LANDING_DROP  — mobile users drop off ~30% more on the landing page (page_view -> view_item).
2. SEA_PREMIUM_GAP      — SEA traffic calculates a premium ~25% less often (view_item -> add_to_cart).
3. PAYMENT_DIP          — a one-week dip in begin_checkout -> add_payment_info for everyone
                          (e.g. a payment-page bug), supported by a customer-service note.

Contentsquare zones, an Optimizely experiment and qualitative notes are generated to match.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from cro.config import AppConfig, get_config

SEED = 20260924
PRODUCT_LINE = "auto"
START_DATE = date(2026, 6, 29)  # a Monday
N_DAYS = 84  # 12 weeks
DAILY_LANDING_USERS = 5_000

DEVICE_SHARE = {"mobile": 0.60, "desktop": 0.33, "tablet": 0.07}
CHANNEL_SHARE = {
    "sea": 0.30,
    "seo": 0.25,
    "direct": 0.15,
    "email": 0.08,
    "paid_social": 0.07,
    "affiliate": 0.10,
    "referral": 0.05,
}

# Baseline transition rate from the previous step into this step.
BASE_RATES = {
    "view_item": 0.55,
    "add_to_cart": 0.45,
    "begin_checkout": 0.30,
    "add_payment_info": 0.65,
    "purchase": 0.80,
}

# Built-in patterns: multipliers on the baseline transition rates.
MOBILE_LANDING_DROP = {"device": "mobile", "step": "view_item", "multiplier": 0.70}
SEA_PREMIUM_GAP = {"channel": "sea", "step": "add_to_cart", "multiplier": 0.75}
PAYMENT_DIP = {
    "step": "add_payment_info",
    "multiplier": 0.60,
    "start": START_DATE + timedelta(days=56),
    "end": START_DATE + timedelta(days=62),
}

# Milder, realistic variation that should not dominate the findings.
CHANNEL_QUALITY = {"email": 1.08, "direct": 1.05, "affiliate": 1.04, "paid_social": 0.92}
TABLET_FACTOR = 0.97
WEEKEND_TRAFFIC = 0.80


def _transition_rate(step: str, device: str, channel: str, day: date) -> float:
    rate = BASE_RATES[step]
    if device == MOBILE_LANDING_DROP["device"] and step == MOBILE_LANDING_DROP["step"]:
        rate *= MOBILE_LANDING_DROP["multiplier"]
    if channel == SEA_PREMIUM_GAP["channel"] and step == SEA_PREMIUM_GAP["step"]:
        rate *= SEA_PREMIUM_GAP["multiplier"]
    if step == PAYMENT_DIP["step"] and PAYMENT_DIP["start"] <= day <= PAYMENT_DIP["end"]:
        rate *= PAYMENT_DIP["multiplier"]
    if step in ("add_to_cart", "purchase"):
        rate *= CHANNEL_QUALITY.get(channel, 1.0)
    if device == "tablet":
        rate *= TABLET_FACTOR
    return min(rate, 0.99)


def generate_funnel_steps(config: AppConfig | None = None, seed: int = SEED) -> pd.DataFrame:
    config = config or get_config()
    rng = np.random.default_rng(seed)
    steps = config.funnel.step_ids
    rows = []
    for offset in range(N_DAYS):
        day = START_DATE + timedelta(days=offset)
        traffic = DAILY_LANDING_USERS * (WEEKEND_TRAFFIC if day.weekday() >= 5 else 1.0)
        for device, d_share in DEVICE_SHARE.items():
            for channel, c_share in CHANNEL_SHARE.items():
                users = int(rng.poisson(traffic * d_share * c_share))
                rows.append((day, steps[0], device, channel, users))
                for step in steps[1:]:
                    users = int(rng.binomial(users, _transition_rate(step, device, channel, day)))
                    rows.append((day, step, device, channel, users))
    df = pd.DataFrame(rows, columns=["date", "step", "device", "channel", "users"])
    df.insert(1, "product_line", PRODUCT_LINE)
    df["source"] = "dummy"
    return df


def generate_cs_zones(funnel: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """Landing-page zones. Mobile: CTA and price indication largely below the fold."""
    rng = np.random.default_rng(seed + 1)
    landing = funnel[funnel["step"] == "page_view"].groupby("device")["users"].sum()
    # zone: (exposure desktop, exposure mobile, attractiveness)
    zones = {
        "hero_banner": (0.99, 0.98, 0.04),
        "cta_bereken_premie": (0.93, 0.46, 0.52),
        "prijsindicatie": (0.88, 0.31, 0.18),
        "usp_blok": (0.71, 0.52, 0.06),
        "trust_reviews": (0.49, 0.22, 0.09),
        "keurmerken_anwb": (0.38, 0.17, 0.05),
        "faq": (0.27, 0.19, 0.21),
    }
    rows = []
    period_end = START_DATE + timedelta(days=N_DAYS - 1)
    for device, pageviews in landing.items():
        for zone, (exp_desktop, exp_mobile, attract) in zones.items():
            exposure = exp_mobile if device == "mobile" else exp_desktop * (0.97 if device == "tablet" else 1.0)
            exposure = float(np.clip(exposure + rng.normal(0, 0.01), 0, 1))
            attractiveness = float(np.clip(attract + rng.normal(0, 0.005), 0, 1))
            click_rate = exposure * attractiveness
            rows.append(
                {
                    "period_start": START_DATE,
                    "period_end": period_end,
                    "product_line": PRODUCT_LINE,
                    "page": "/verzekeringen/autoverzekering",
                    "zone": zone,
                    "device": device,
                    "exposure_rate": round(exposure, 4),
                    "click_rate": round(click_rate, 4),
                    "hover_rate": round(float(np.clip(exposure * 0.3 + rng.normal(0, 0.01), 0, 1)), 4),
                    "conversion_rate_after_click": round(float(np.clip(0.35 + rng.normal(0, 0.03), 0, 1)), 4),
                    "attractiveness_rate": round(attractiveness, 4),
                    "rage_clicks": int(rng.poisson(pageviews * 0.0004 if zone == "prijsindicatie" else pageviews * 0.0001)),
                    "pageviews": int(pageviews),
                }
            )
    return pd.DataFrame(rows)


def generate_experiments(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 2)
    specs = [
        # (id, name, variant, is_control, visitors, true rate, start, end, status)
        ("AUTO-LP-012", "Sticky CTA 'Bereken je premie' op mobiel", "controle", True, 41_200, 0.172,
         START_DATE + timedelta(days=14), START_DATE + timedelta(days=41), "concluded"),
        ("AUTO-LP-012", "Sticky CTA 'Bereken je premie' op mobiel", "sticky_cta", False, 41_050, 0.186,
         START_DATE + timedelta(days=14), START_DATE + timedelta(days=41), "concluded"),
        ("AUTO-LP-015", "Prijsindicatie boven de vouw", "controle", True, 9_800, 0.231,
         START_DATE + timedelta(days=70), None, "running"),
        ("AUTO-LP-015", "Prijsindicatie boven de vouw", "prijs_boven_vouw", False, 9_760, 0.236,
         START_DATE + timedelta(days=70), None, "running"),
    ]
    rows = []
    for exp_id, name, variant, is_control, visitors, rate, start, end, status in specs:
        rows.append(
            {
                "experiment_id": exp_id,
                "name": name,
                "product_line": PRODUCT_LINE,
                "variant": variant,
                "is_control": is_control,
                "metric": "add_to_cart",
                "visitors": visitors,
                "conversions": int(rng.binomial(visitors, rate)),
                "start_date": start,
                "end_date": end,
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def generate_qual_notes() -> pd.DataFrame:
    d = lambda days: START_DATE + timedelta(days=days)  # noqa: E731
    notes = [
        ("Q-001", d(10), "kwalitatief", "usertest", "view_item", "device=mobile",
         "4 van 6 mobiele deelnemers scrolden voorbij de hero zonder de knop 'Bereken je premie' te zien.",
         "cta;mobiel;boven-de-vouw"),
        ("Q-002", d(12), "kwalitatief", "usertest", "view_item", "",
         "Deelnemers wilden eerst een prijsindicatie zien voordat ze gegevens invulden.",
         "prijsindicatie;verwachting"),
        ("Q-003", d(20), "sitegedrag", "sessierecording", "view_item", "channel=sea",
         "Bezoekers vanuit SEA-advertenties 'vanaf € 25 p/m' zoeken dat bedrag op de landingspagina en haken af.",
         "sea;verwachtingsmismatch;prijs"),
        ("Q-004", d(30), "kwalitatief", "survey", "add_to_cart", "",
         "Exit-survey: 'Ik moest te veel invullen voordat ik een prijs zag' (18% van de antwoorden).",
         "formulier;prijsindicatie"),
        ("Q-005", d(35), "markt", "marktonderzoek", "page_view", "",
         "Drie van de vier grote concurrenten tonen een prijsindicatie boven de vouw op mobiel.",
         "concurrentie;prijsindicatie"),
        ("Q-006", d(40), "kwalitatief", "usertest", "page_view", "",
         "Het ANWB-merk wekt vertrouwen, maar reviews en keurmerken worden op mobiel nauwelijks gezien.",
         "trust;reviews;mobiel"),
        ("Q-007", d(58), "kwalitatief", "klantenservice", "add_payment_info", "",
         "Piek in klantcontacten over een foutmelding bij het invullen van IBAN (week van 24 augustus).",
         "betaling;bug;iban"),
        ("Q-008", d(63), "sitegedrag", "sessierecording", "page_view", "device=mobile",
         "Landingspagina laadt op mobiel traag (LCP ~3,8 s); rage clicks op de prijsindicatie tijdens het laden.",
         "laadsnelheid;mobiel;rage-clicks"),
    ]
    return pd.DataFrame(
        notes, columns=["note_id", "date", "pillar", "source", "step", "segment", "observation", "tags"]
    ).assign(product_line=PRODUCT_LINE)


def generate_all(config: AppConfig | None = None, seed: int = SEED) -> dict[str, pd.DataFrame]:
    funnel = generate_funnel_steps(config, seed)
    return {
        "funnel_steps": funnel,
        "cs_zones": generate_cs_zones(funnel, seed),
        "experiments": generate_experiments(seed),
        "qual_notes": generate_qual_notes(),
    }


def write_all(out_dir: Path, config: AppConfig | None = None, seed: int = SEED) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, df in generate_all(config, seed).items():
        path = out_dir / f"{name}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        paths[name] = path
    return paths
