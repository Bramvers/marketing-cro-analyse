# Startprompt voor Claude Code

Plak dit in Claude Code in de root van de repo `marketing-cro-analyse`, nadat `CLAUDE.md` erin staat. Start bij voorkeur in **plan mode**.

---

Je gaat de CRO Analyse Tool voor ANWB Verzekeringen bouwen. Lees eerst `CLAUDE.md` (projectregels en scope) en `index.html` (het concept zoals het intern gepresenteerd is).

**Doel van de eerste versie:** een lokale Streamlit-app die voor Autoverzekering de funnel-uitval van landingspagina tot purchase analyseert, verklaart met gedragssignalen, en eindigt in een rapport met ICE-geprioriteerde, onderbouwde testhypotheses. Data komt binnen via CSV-uploads en screenshots; voor ontwikkeling gebruik je gegenereerde dummydata.

**Stap 1 — Plan (nog geen code):**
1. Vat in maximaal 10 regels samen wat je begrijpt van het doel, de scope en wat expliciet buiten scope valt.
2. Stel je vragen over onduidelijkheden, vooral over de funnel-mapping (welke GA4-stap is premieberekening?), de verwachte CSV-formaten per bron en de rapportstructuur.
3. Stel een genormaliseerd datamodel voor (tabellen, kolommen, types) voor funneldata, Contentsquare-zonedata, Optimizely-experimentdata en kwalitatieve notities.
4. Werk de fases hieronder uit tot concrete taken met een acceptatiecriterium per fase.

Wacht op mijn akkoord voordat je gaat bouwen.

**Fases:**
- **Fase 1 — Fundament:** projectstructuur, venv-instructies voor Windows zonder admin, `config/funnel.yaml`, datamodel met validatie, dummy-datagenerator met ingebouwde patronen, lege Streamlit-app met navigatie. *Klaar als:* `streamlit run app.py` draait en dummydata valideert zonder fouten.
- **Fase 2 — Import:** upload-pagina voor CSV's per bron, mapping naar het datamodel, duidelijke validatiemeldingen (ontbrekende kolommen, onlogische aantallen, kleine samples). *Klaar als:* dummy-CSV's en een bewust kapotte CSV correct worden afgehandeld.
- **Fase 3 — Funnelanalyse:** drop-off per stap, uitgesplitst naar device, kanaal en periode; significantietoets bij segmentverschillen; plotly-funnel en vergelijkingsgrafieken. *Klaar als:* de ingebouwde patronen in de dummydata zichtbaar én statistisch onderbouwd naar voren komen, met pytest-dekking op de rekenlogica.
- **Fase 4 — Synthese:** LLM-stap die alleen berekende resultaten krijgt, bevindingen formuleert met evidence-ID's en hypotheses opstelt in het vaste format met ICE-score. Hypotheses bewerkbaar in de UI. *Klaar als:* elke hypothese naar concreet bewijs verwijst en de app ook zonder API key werkt (synthese dan uitgeschakeld).
- **Fase 5 — Rapport:** rapport volgens de vaste structuur uit `CLAUDE.md`, status concept/gereviewd, export naar Markdown en HTML. *Klaar als:* een compleet Auto-rapport uit dummydata te exporteren is.
- **Fase 6 — Screenshot-extractie:** de bestaande extractie uit `index.html` overzetten naar een Streamlit-pagina (screenshot → Claude → bewerkbare tabel → toevoegen aan dataset). *Klaar als:* een screenshot van een dashboard bruikbare, gecorrigeerde metrics oplevert.

**Na elke fase:** draai de tests, geef een korte samenvatting (wat is gebouwd, wat niet, open vragen, bekende beperkingen) en stop voor mijn review.

**Buiten scope nu:** live API-koppelingen (BigQuery, Contentsquare, Optimizely), hosting, authenticatie, andere productlijnen dan Auto. Ontwerp wel zo dat die later aan te sluiten zijn.
