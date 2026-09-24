# CRO Analyse Tool — ANWB Verzekeringen

Lokale Streamlit-tool die CRO-data (GA4/BigQuery, Contentsquare, Optimizely, kwalitatieve notities) samenbrengt tot één onderbouwd rapport: **wat zien we, waarom gebeurt het, en wat is de volgende test.** Zie `CLAUDE.md` voor projectregels en `index.html` voor het concept.

## Installatie (Windows, zonder admin-rechten)

Vereist: Python 3.11 of hoger (getest met 3.14). Zet de repo bij voorkeur buiten OneDrive, bijvoorbeeld in `C:\dev\`.

```powershell
cd C:\dev\marketing-cro-analyse
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env   # vul ANTHROPIC_API_KEY en ANTHROPIC_MODEL in (pas nodig vanaf fase 4)
```

Geeft `Activate.ps1` een fout over het uitvoeren van scripts? Zet het beleid alleen voor je eigen account (geen admin nodig):

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Of sla activeren over en roep de venv direct aan: `.\.venv\Scripts\python.exe -m streamlit run app.py`.

## Gebruik

```powershell
streamlit run app.py                 # start de app op http://localhost:8501
python scripts/generate_dummy.py     # (her)genereer en valideer data/dummy/*.csv
pytest                               # draai de tests
```

Klik in de app op **Dummydata laden** om de volledige pipeline zonder echte data te testen.

## Structuur

```
app.py                 Streamlit-entry met navigatie
pages/                 Overzicht, Upload, Funnelanalyse, Hypotheses, Rapport, Screenshot-extractie
config/funnel.yaml     Funnelstappen, micro/macro-conversie, productlijnen, segmenten, drempels
cro/config.py          Laden en valideren van funnel.yaml
cro/model/             Genormaliseerd datamodel (schema's) en validatie
cro/sources/           Loaders per bron (CSV nu, API later) achter één interface
cro/dummy.py           Dummydata met ingebouwde patronen
cro/analysis/          (fase 3) funnel, segmenten, statistiek
cro/synthesis/         (fase 4) LLM-synthese met evidence-ID's
cro/report/            (fase 5) rapport en export
data/dummy/            Gegenereerde testdata (wel in git); overige data/ staat in .gitignore
```

## Dummydata: ingebouwde patronen

12 weken dagdata (29 juni t/m 20 september 2026) voor Autoverzekering, met vaste seed:

1. **Mobiel haakt vaker af op de landingspagina**: page_view → view_item is ~30% lager dan op desktop.
2. **SEA berekent minder vaak een premie**: view_item → add_to_cart is ~25% lager dan bij andere kanalen.
3. **Betaaldip**: in de week van 24 augustus daalt begin_checkout → add_payment_info met ~40%.

Contentsquare-zones (CTA en prijsindicatie op mobiel onder de vouw), twee Optimizely-experimenten en acht kwalitatieve notities sluiten hierop aan.
