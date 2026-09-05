# racecenter_vuelta_2026_stages.json

Echte respons van `https://racecenter.lavuelta.es/api/stage-2026`, opgehaald
op 27 augustus 2026 en hier geplakt door de eigenaar — de proxy in de
ontwikkelomgeving laat ASO niet door.

**Ingekort, niet verzonnen.** Van de drie bewaarde etappes staan alle
etappevelden er letterlijk zoals ze binnenkwamen. Weggelaten zijn alleen de
toeristische teksten (`content.texts`, drie talen per plaats) en de
`img.aso.fr`-plaatjes: samen tientallen kilobytes prietpraat waar deze
integratie niets mee doet. Van `departureCity`/`arrivalCity` zijn `id`,
`code`, `label` en `country` blijven staan, want dat is wat we zouden
gebruiken.

Wat hiermee vaststaat:

- De Vuelta draait hetzelfde Race Center-platform als de Tour: dezelfde
  `/api/{bind}-{jaar}`-vorm en dezelfde velden.
- Elke etappe draagt `stage`, `date`, `startTime`, `endTime`, `length` /
  `lengthDisplay`, `type` (`MMG`, `PLN`, …), `departureCity.label`,
  `arrivalCity.label`, `timezone`, `hasCoordinates`, `isCancelled` en
  `showGroups`.
- De lijst komt **niet** op etappenummer binnen.
- `isCancelled` bestaat en staat op `true` voor etappe 3 (24 augustus,
  Gruissan → Font Romeu). Cyclingstage kent dat begrip niet.

Wat hiermee **niet** vaststaat: of er een km-to-go in de live-feed zit. Daar
is `/live-stream` of `/api/telemetryCompetitor-2026` voor nodig.
