# Resultatenindex van de Vuelta 2026, opgehaald 12 september 2026

`https://www.cyclingstage.com/vuelta-2026-results/` — door de eigenaar in een
browser opgeslagen, want de proxy in de ontwikkelomgeving laat cyclingstage
niet door (403 op de CONNECT).

Waarom er twee van deze pagina's in `tests/fixtures/` staan:

| bestand | etappes | waarvoor |
|---|---:|---|
| `cyclingstage_vuelta_2026_results_index.html` | 15 | het geval "het overzicht kent de etappe van vandaag nog niet" |
| dit bestand | 20 | de opmaak van de pagina, en dat het afgeleide adres klopt |

## Wat deze pagina vaststelt

1. **`uitslag_url` leidt het juiste adres af.** Voor etappe 18 — de tijdrit
   die op 10 september geen uitslag opleverde — staat er letterlijk
   `/vuelta-2026-results/stage-18-spain-results-2026/`, precies wat de code
   bouwt. Een tijdrit krijgt dus géén afwijkend adres, en daarmee is die
   verklaring van de baan.
2. **De opmaak van de indexpagina zelf.** Tot nu toe stond in CLAUDE.md dat
   die niet geverifieerd was; `parse_uitslag_index` leest er alle twintig
   etappes correct uit.
3. **Een eendaagse koers zet zijn uitslag onder een onraadbare afkorting.**
   In de menubalk staat `href="/gp-quebec-2026/results-gpq-2026 "` met
   `title="GP Quebéc 2026 Results"`. Het gebouwde `/gp-quebec-2026-results/`
   gaf een 404 — dat had de eigenaar op 7 september al gemeld. Let op de
   spatie binnen de `href`: die moet eraf, anders bestaat het adres niet.

## Wat deze pagina níét vaststelt

Waarom de uitslag van etappe 18 op 10 september om negen uur 's avonds niet
binnenkwam. Het adres was goed en de uitslag bestaat (de kop "Küng storms to
glory, Mas retains lead" staat op deze pagina), dus het ging om het moment:
op dat uur stond de uitslag er nog niet, of nog niet in de vorm die
`parse_uitslag` leest. Van hieruit niet na te kijken.
