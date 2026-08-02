# worldtour_next_race

Home Assistant custom component die wielerdata toont op een dashboard (Raspberry Pi 5, HAOS).

## Taal
Antwoord altijd in het Nederlands.

## Kernprincipe
Schone data boven fabricatie. Bestaat betrouwbare data niet, toon dan niets —
liever een leeg vak dan iets misleidends. Concreet: geen gereconstrueerd
hoogteprofiel wanneer er geen GPX beschikbaar is.

## Databronnen
- ProCyclingStats: klassementen, startlijsten
- wielerflits.nl: tv-uitzendtijden (tekst met tijden; logo-hotlinking is
  geprobeerd en bewust verlaten)
- cyclingstage.com: geschatte finishtijden, GPX-routes

## Vaste valkuilen
- **PCS naamuitlijning**: `rider_name` verzamelt renner-links tabelbreed als
  platte lijst, terwijl tijd en team per rij worden gelezen. Rijen met extra
  links laten namen verschuiven. Opgelost via per-rij namen lezen
  (`_row_names()`), herstel via `_repair_rows()` met de startlijst als
  betrouwbare renner-teamreferentie, en volgorde-onafhankelijke naamsleutels.
  Niet terugdraaien naar tabelbrede verzameling.
- **Dagwinst**: gaat via koppeling op de "Prev"-rangkolom, waarbij de vorige
  etappestand als {positie: tijd} wordt opgehaald. De "Time won/lost"-kolom van
  PCS is JavaScript-gerenderd en onbruikbaar. Vergelijken met de vorige stand is
  te fragiel gebleken.

## Technisch
- GPX-downsampling via LTTB (vormbehoudend)
- Klimdetectie: standaard col-detectie plus tweede drempel voor korte, steile
  klimmen (type Montmartre)
- `GPX_OVERRIDE` dict voor handmatige URL-invoer bij races zonder publieke GPX

## Testen
Je kunt geen draaiende Home Assistant bereiken. Test parserlogica tegen de
opgeslagen HTML-fixtures in `tests/fixtures/`. Verzin geen livedata.
