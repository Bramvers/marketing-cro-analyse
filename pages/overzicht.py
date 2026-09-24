import streamlit as st

from cro.config import get_config
from cro.model import ALL_SCHEMAS
from cro.ui import datasets, load_dummy_data, render_report

config = get_config()

st.title("CRO Analyse — ANWB Verzekeringen")
st.markdown(
    "Van ruwe gedragsdata naar een onderbouwd CRO-besluit: **wat zien we, waarom gebeurt het, "
    "en wat is de volgende test.**"
)

with st.expander("Funnelconfiguratie (config/funnel.yaml)", expanded=False):
    labels = {s.id: s.label for s in config.funnel.steps}
    st.markdown(" → ".join(f"`{s.id}` ({s.label})" for s in config.funnel.steps))
    st.markdown(
        f"- Micro-conversie (premieberekening): **{labels[config.funnel.micro_conversion]}**\n"
        f"- Macro-conversie: **{labels[config.funnel.macro_conversion]}**\n"
        f"- Telling: **{'gebruikers' if config.funnel.counting_unit == 'users' else 'sessies'}**, "
        f"**{'open' if config.funnel.funnel_type == 'open' else 'gesloten'}** funnel\n"
        f"- Actieve productlijnen: {', '.join(p.label for p in config.product_lines if p.enabled)}"
    )

st.subheader("Datasets in deze sessie")
if st.button("Dummydata laden (Autoverzekering)", type="primary"):
    load_dummy_data()

loaded = datasets()
if not loaded:
    st.info("Nog geen data geladen. Laad de dummydata hierboven, of upload CSV's via **Upload** (fase 2).")
for table in ALL_SCHEMAS:
    if table in loaded:
        render_report(loaded[table].report)
