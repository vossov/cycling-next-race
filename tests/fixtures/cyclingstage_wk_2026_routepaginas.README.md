# cyclingstage_wk_2026_route_itt.html en _route_wegrit.html

```
https://www.cyclingstage.com/world-championships-2026-montreal/route-itt-wc-2026/
https://www.cyclingstage.com/world-championships-2026-montreal/route-road-race-wc-2026/
```

Opgehaald 20 september 2026 door de eigenaar. Dit zijn de pagina's waar de
programmatabel van het WK per onderdeel naar linkt (zie
`cyclingstage_wk_2026_montreal.README.md`). Beide tijdritten delen de eerste
— ze rijden dezelfde route.

## Wat er op staat

| | tijdrit | wegrit mannen |
|---|---|---|
| starttijd | `9:19` (vrouwen; mannen 12:45) | `9:00` |
| verwachte finish | — | `15:40` |
| tijdzone | `local time (TDE)` | `local times (EDT)` |
| hoogtemeters | `220 metres of elevation gain` | `3,800 metres of elevation gain` |
| GPX | geen | `cdn…/images/world-championships/2026/route.gpx` |

Drie dingen die hier voor het eerst uitkwamen, alle drie hier nagemeten:

- **De tijden staan in de tijd van de kóérs, niet in die van ons.** `9:00
  EDT` is 15:00 in Nederland. De pagina zegt zelf welke zone het is, dus
  `_naar_lokale_klok` rekent het om; zonder dat meldde de tegel LIVE terwijl
  er nog niemand gereden had en stond de geschatte stip zes uur vooruit.
  `TDE` is geen tijdzone maar de typefout van de site voor `EDT` — net als
  `hils` voor `hills` in de Vuelta-tabel.
- **"expected to finish at" in plaats van "around".** De Vuelta schrijft
  "around"; met alleen dat woord in de regex bleef de finishtijd hier leeg.
- **De GPX van de wegrit heet `route.gpx`** — precies het bestand dat
  `gpx_urls` bouwt voor een eendaagse koers, in de map die álle onderdelen
  delen. De tijdrit van 39 km zou daarmee het profiel van 273 km krijgen.
  Voor een onderdeel telt daarom alleen het adres dat zijn eigen pagina
  noemt, en `_profiel_past` meet de lengte na tegen de programmatabel.

## Wat hier nog niet van is nagekeken

De routepagina van de **wegrit voor vrouwen**
(`route-road-race-wc-2026-women/`) en die van de gemengde estafette (die
bestond nog niet, de tabel zei "to follow"). Of de vrouwenpagina een eigen
GPX noemt of diezelfde `route.gpx` is dus niet bekend — vandaar dat
`_profiel_past` er is.
