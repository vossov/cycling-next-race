# wielerflits_tv_2026-09-07.html

De pagina `https://www.wielerflits.nl/nieuws/wielrennen-op-tv/` zoals hij op
7 september 2026 was, door de eigenaar opgeslagen in Safari en hier uit het
webarchive gehaald. De proxy in de ontwikkelomgeving laat wielerflits niet
door.

**Tot deze fixture draaide `_parse_channels` volledig op HTML die ikzelf had
getypt** — de enige parser in dit project waarvoor dat gold. Wat er daardoor
niet was opgevallen:

1. `_channels_from` matcht op `race/{slug}/{jaar}`, een procyclingstats-pad.
   Sinds 0.19 komt daar een cyclingstage-adres binnen, dus de match faalt en
   er komt voor **elke** koers een lege lijst terug. De tv-gids was al
   maanden stil dood.
2. Een **eendaagse koers** staat als `/wielerkalender/{slug}/startlijst`,
   niet als `/wielerkalender/{slug}/etappes/{n}/`. De regex eiste die tweede
   vorm, dus eendaagse koersen konden sowieso nooit zenders krijgen.
3. Koppelen op slug-prefix geeft **valse treffers**: `giro` matcht
   `giro-della-toscana-...` en `tour-de-france` matcht
   `tour-de-france-femmes-we-2026`. Verkeerde zenders is erger dan geen.

Wat er op de pagina staat: zes Vuelta-etappes (16 t/m 21) en acht eendaagse
koersen, met per uitzending een tijd, een zenderlogo en vlaggen voor de
landen waar hij te zien is. Let op dat er óók een landvlag vóór de koersnaam
staat — dat is het land van de kóérs, niet van de uitzending.

Etappe 19 en 20 hebben er drie: HBO Max (BE+NL), Sporza online (alleen BE) en
VRT1 (BE+NL). Dat maakt het een goede test voor het NL-filter.
