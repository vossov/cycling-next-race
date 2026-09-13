# Uitslag van GP Québec 2026 — de eerste eendaagse in de fixtures

`https://www.cyclingstage.com/gp-quebec-2026/results-gpq-2026/`, gereden
11 september 2026, door de eigenaar in een browser opgeslagen (de proxy in de
ontwikkelomgeving laat cyclingstage niet door, 403 op de CONNECT).

Dit is de pagina waar 0.29.3 op gokte en die 0.29.4 bewijst.

## Wat hij vaststelt

1. **Het adres dat `uitslag_kandidaten` oplevert is het echte adres**, tot en
   met de slash: `/gp-quebec-2026/results-gpq-2026/`. Het gebouwde
   `/gp-quebec-2026-results/` gaf een 404.
2. **`parse_uitslag` kan een eendaagse uitslag lezen.** De kop is
   `Results 2026 GP Quebec` — geen "Stage N Results", maar hij bevat "result"
   en valt dus in `results`. Tien renners, met land en tijd:
   Evenepoel 4:40:21, Ciccone s.t., Charmig +0:15.
3. **Er is geen klassement, en dat blijft leeg.** `gc`, `points`, `kom` en
   `youth` komen er alle vier op nul uit — een eendaagse koers heeft er geen,
   en er wordt niets bij verzonnen.
4. **Elke pagina onder de koersmap draagt de link.** Deze uitslagpagina noemt
   zijn eigen adres in de menubalk, dus de koerspagina — waar de code kijkt —
   doet dat ook.

## De keten die hiermee rond is

| stap | uitkomst |
|---|---|
| kalender | `url = /gp-quebec-2026/`, routekolom leeg |
| `_cs_event_stages` | eendaags, `stage_url = race_url` |
| `uitslag_index_url` | `/gp-quebec-2026-results/` → 404 |
| `uitslag_kandidaten` | `/gp-quebec-2026/results-gpq-2026/` |
| `parse_uitslag` | tien renners |

Vóór 0.29.3 stopte dat na de derde regel, zonder fout in het log.
