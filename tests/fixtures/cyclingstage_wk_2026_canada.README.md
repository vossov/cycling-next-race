# cyclingstage_wk_2026_canada.html

`https://www.cyclingstage.com/world-championships-2026-canada/`, opgehaald
7 september 2026.

Een van de zes koersen waarvan de kalender geen routeadres geeft. De
koerspagina linkt naar géén enkele subpagina, dus `route_kandidaten` vindt
niets — de programmatabel staat op de koerspagina zelf.

## Waarom het WK tot 0.31 onzichtbaar was

De tabel heeft evenveel kolommen als een etappetabel, maar ze betekenen iets
anders:

| | kolom 1 | kolom 2 | kolom 3 | kolom 4 | kolom 5 |
|---|---|---|---|---|---|
| rittenkoers | nummer | datum | start - finish | km | type |
| kampioenschap | **datum** | start - finish | type | km | el.gain |

`_etapperijen` eist een nummer in de eerste kolom en sloeg daarom élke rij
over. Nul etappes, en een koers zonder etappes valt stil weg.

## Wat er wél in staat

```
20-9 | Montreal            | ITT (v)      |  39.9 |   195
20-9 | Montreal            | ITT (m)      |  39.9 |   195
23-9 | Montreal            | mixed relay  |  40.4 |   262
26-9 | Brossard - Montreal | wegrace (v)  | 180.0 | 2,502
27-9 | Brossard - Montreal | wegrace (m)  | 273.2 | 3,720
```

Datum, route, onderdeel, afstand én hoogtemeters — en het geslacht staat er
letterlijk bij, `(v)` of `(m)`. `parse_programma` leest dit sinds 0.31.

Drie dingen om op te letten, alle drie hier nagemeten:

- **De komma in `2,502` is een duizendtalscheiding**, geen decimaalteken.
  `_getal` zou er 2,502 meter van maken; `_hoogtemeters` doet het goed.
- **Twee onderdelen op één dag** (beide tijdritten op 20 september). "Wat er
  nog komt" was alleen een látere dag, dus het tweede onderdeel was nergens
  te zien.
- **Geen enkel onderdeel heeft een eigen adres.** Daarom krijgt elk
  onderdeel het koersadres met het onderdeel als fragment
  (`...-canada/#tijdrit-vrouwen`); zonder dat vallen vijf onderdelen samen
  tot één, want `stage_url` is de sleutel van de ontdubbeling en van vier
  caches.

## Wat hier nog steeds niet uit komt

Een **uitslag** en een **hoogteprofiel** per onderdeel. Daar is een adres per
onderdeel voor nodig en dat staat er niet in. Die velden blijven dus leeg —
het programma tonen kan wel, en dat is waar het om ging.

## Deze pagina bestaat niet meer — en blijft juist daarom staan

Het adres hierboven geeft sinds ongeveer 20 september 2026 een 404: het WK is
verhuisd naar `/world-championships-2026-montreal/`. Die pagina staat als
`cyclingstage_wk_2026_montreal.html` ernaast.

Deze versie blijft staan omdat de twee samen de test zijn voor het lezen van
de programmatabel: dezelfde vijf onderdelen, twee echte kolomvolgordes.

```
 7 september (hier):  datum | route | type  | km | el.gain
20 september:         datum | type  | route | km | el.gain | riders
```

Op de tegel van 20 september stond daardoor "Montreal" waar "Tijdrit mannen"
hoorde te staan. Sinds 0.31.1 worden de kolommen op inhoud gelezen.
