# cyclingstage_wk_2026_montreal.html

`https://www.cyclingstage.com/world-championships-2026-montreal/`, opgehaald
20 september 2026 door de eigenaar — de dag van beide tijdritten.

**De koers is verhuisd.** Het adres uit
`cyclingstage_wk_2026_canada.README.md` geeft inmiddels een 404. De kalender
wijst zelf naar het nieuwe adres, dus daar hoefde niets voor te veranderen;
het is wel een ándere pagina.

## Wat er anders is dan op 7 september

```
 7 september:  datum | route | type  | km | el.gain
20 september:  datum | type  | route | km | el.gain | riders
```

Kolom 2 en 3 zijn omgedraaid en er is een kolom bij. Dáárdoor las de tegel
"Montreal · World Championships" waar "Tijdrit mannen" hoorde te staan:
`parse_programma` las kolom 3 als het onderdeel. Sinds 0.31.1 worden de
kolommen op inhoud gelezen, en deze twee pagina's zijn samen de test — twee
echte volgordes van dezelfde tabel.

De site schrijft het ook anders op: `ITT (w)` en `road race (m)` in plaats
van `ITT (v)` en `wegrace (v)`. Allebei herkend.

```
20-9 | ITT (w)        | Montreal            |  39.2 |   220 | riders
20-9 | ITT (m)        | Montreal            |  39.2 |   220 | riders
23-9 | mixed relay    | Montreal            |  40.6 |   290 | to follow
26-9 | road race (w)  | Brossard - Montreal | 180.1 | 2,570 | riders
27-9 | road race (m)  | Brossard - Montreal | 273.4 | 3,808 | riders
```

## Een adres per onderdeel — nieuw

De routekolom linkt nu per onderdeel:

| onderdeel | routepagina |
|---|---|
| beide tijdritten | `/route-itt-wc-2026/` — dezelfde route, dus één pagina |
| wegrit vrouwen | `/route-road-race-wc-2026-women/` |
| wegrit mannen | `/route-road-race-wc-2026/` |
| gemengde estafette | geen (de kolom `riders` zegt "to follow") |

Daarom blijft het fragment nodig ook al ís er een adres: zonder
`#tijdrit-mannen` vallen de twee tijdritten alsnog samen.

Wat op die routepagina's staat is **niet nagekeken** — ze zijn niet
opgehaald. Ze staan in `docs/gevraagde-paginas.md`.

## De 3 800 hoogtemeters

Op deze pagina staat in lopende tekst `3,800 metres of elevation gain`,
naast `220` en `2,570`. Die zin gaat over de wegrit van de mannen (de tabel
zegt daar 3 808) en kwam via `_fetch_stage_meta` op álle vijf de onderdelen
terecht — ook op de tijdrit van 39 km, die daarmee "Bergrit" heette. De
tabel wint sinds 0.31.2 van de lopende tekst.
