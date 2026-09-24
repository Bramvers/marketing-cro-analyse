# CLAUDE.md — CRO Analyse Tool (ANWB Verzekeringen)

## Wat we bouwen
Een lokale Streamlit-tool die CRO-data uit verschillende bronnen samenbrengt tot één onderbouwd rapport: **wat zien we, waarom gebeurt het, en wat is de volgende test.**
Het concept staat beschreven in `index.html` (pipeline, doelen, output, risico's). Lees dat bestand bij de start.

Eerste use case (MVP): **funnel drop-off per productlijn**, te beginnen met Autoverzekering.
Productlijnen: Auto, Woon, Reis, Fiets, Bromfiets.

## Domeincontext
- Micro-conversie: **premieberekening**. Macro-conversie: **purchase**.
- GA4 e-commerce funnel: `page_view → view_item → add_to_cart → begin_checkout → add_payment_info → purchase`.
- De koppeling tussen funnelstappen en premieberekening/purchase leg je vast in `config/funnel.yaml` — niet hardcoden, want de mapping moet nog bevestigd worden.
- Bekende hypotheses Auto (landingspagina → funnelinstap): sticky CTA, prijsindicatie boven de vouw, trust-elementen, SEA-verwachtingsmismatch, laadsnelheid.
- CRO-onderzoek rust op drie pijlers: eigen sitegedrag (GA4 + Contentsquare), kwalitatief onderzoek, marktonderzoek.

## Scope MVP
- **Data-invoer via uploads**: CSV-exports (GA4/BigQuery, Contentsquare, Optimizely) en screenshots. Géén API-koppelingen in de MVP. Meerdere datasets op sessieniveau (bijv. sessiedata + ecommerce-data) koppelt de tool zelf op `session_id`, met controles op uniciteit, niet-matchende sessies en 1-op-n-relaties (zie Privacy & data).
- Een **dummy-datagenerator** met realistische Auto-funnel data, inclusief een paar bewust ingebouwde patronen (bijv. hogere mobiele uitval op de landingspagina, lagere conversie vanuit SEA), zodat de hele pipeline zonder echte data te testen is.
- Latere fase (niet nu bouwen, wel rekening mee houden): BigQuery live, Contentsquare-API, Optimizely-API. Ontwerp daarom een `sources/`-laag met één interface per bron, zodat een CSV-loader later vervangen kan worden door een API-loader.

## Architectuurprincipes
1. **Rekenen in Python, interpreteren met AI.** Alle cijfers (drop-off, segmentverschillen, significantie, confidence intervals) worden deterministisch berekend en getest. Het taalmodel krijgt alleen berekende resultaten en schrijft de interpretatie; het rekent nooit zelf.
2. **Elke bewering heeft bewijs.** Iedere bevinding en hypothese verwijst naar een evidence-ID (tabel, metric, segment). Beweringen zonder bewijs worden niet getoond.
3. **Eén genormaliseerd datamodel** (pydantic/pandas-schema's) waar alle bronnen naartoe worden vertaald. Validatie bij import: ontbrekende kolommen, onlogische waarden (stap N > stap N-1), te kleine samples → duidelijke waarschuwing in de UI.
4. **Vaste rapportstructuur**: Context → Bevindingen → Onderbouwing → Aanbevelingen → Geprioriteerde hypotheses (ICE: impact, confidence, ease) → Meetplan per test.
5. **Hypotheseformat**: *Als we [wijziging] doen voor [segment], dan verwachten we [effect op metric], omdat [observatie + bewijs-ID].*
6. **Menselijke review**: elk rapport heeft status `concept` of `gereviewd`; AI-tekst is visueel herkenbaar als gegenereerd.

## Tech stack
- Python 3.11+, Streamlit, pandas, pydantic, plotly, anthropic SDK, pytest.
- Omgeving: **Windows, geen admin-rechten, OneDrive**. Dus: `python -m venv .venv` + `pip install` zonder admin, geen systeembrede installs, geen Docker. Zet de venv en `data/` buiten OneDrive-sync of in `.gitignore`. Gebruik `pathlib` voor paden.
- Modelnaam en API key via `.env` (`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`) — nooit hardcoden, nooit committen.

## Voorgestelde structuur
```
app.py                 # Streamlit entry
pages/                 # Upload, Funnelanalyse, Hypotheses, Rapport, Screenshot-extractie
cro/
  sources/             # loaders per bron (csv nu, api later)
  model/               # schema's + validatie
  analysis/            # funnel, segmenten, statistiek
  synthesis/           # prompts + LLM-aanroepen, evidence-koppeling
  report/              # template + export (Markdown/HTML)
config/funnel.yaml     # stappen, mapping, productlijnen
data/dummy/            # gegenereerde testdata
scripts/generate_dummy.py
tests/
```

## Privacy & data
- **Sessiedata mag, maar alleen lokaal en kortstondig** (besluit 2026-09-24, optie A). Uploads op sessieniveau (bijv. sessiedata + ecommerce-data, gekoppeld op `session_id`) zijn toegestaan. Pseudonieme ID's (`session_id`, `user_pseudo_id`) gelden als persoonsgegevens, dus:
  - Ruwe sessierijen alleen in het geheugen van de lopende sessie: nooit naar schijf, nooit in git, nooit in logs of foutmeldingen.
  - Direct na koppelen en valideren aggregeren (aantallen per stap, segment, periode). Alleen die aggregaten gaan verder de pipeline in (analyse, synthese, rapport).
  - Geen directe persoonsgegevens (naam, e-mail, kenteken, postcode+huisnummer, IP) in uploads; kolommen die daarop lijken → upload weigeren met een duidelijke melding.
  - Rapporten en exports bevatten nooit ID's of rijen op sessieniveau.
- Echte exports nooit in git (`data/` behalve `data/dummy/` in `.gitignore`). Dummydata bevat alleen verzonnen ID's.
- Stuur naar de API alleen geaggregeerde, berekende resultaten — nooit ruwe of sessiedata.
- Sessiesleutel GA4: `ga_session_id` is alleen uniek per gebruiker; gebruik `user_pseudo_id` + `ga_session_id` als `session_id`.

## Werkafspraken
- Werk in fases; stop na elke fase voor review. Kleine, afgeronde stappen boven grote halve.
- Feature branch + pull request per fase; duidelijke commitberichten.
- Tests voor alle rekenlogica in `analysis/`. Draai `pytest` voor je een fase afrondt.
- UI-teksten en rapporten in het **Nederlands**; code, variabelen en docstrings in het Engels.
- Twijfel over domein of data-mapping? Vraag het, niet gokken.
