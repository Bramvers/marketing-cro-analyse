"""Streamlit entry point: `streamlit run app.py`."""

import streamlit as st

st.set_page_config(page_title="CRO Analyse — ANWB Verzekeringen", page_icon="📊", layout="wide")

navigation = st.navigation(
    {
        "Start": [st.Page("pages/overzicht.py", title="Overzicht", icon="🏠", default=True)],
        "Analyse": [
            st.Page("pages/upload.py", title="Upload", icon="📥"),
            st.Page("pages/funnelanalyse.py", title="Funnelanalyse", icon="📉"),
            st.Page("pages/hypotheses.py", title="Hypotheses", icon="💡"),
            st.Page("pages/rapport.py", title="Rapport", icon="📄"),
        ],
        "Hulpmiddelen": [st.Page("pages/screenshot_extractie.py", title="Screenshot-extractie", icon="🖼️")],
    }
)
navigation.run()
