# aso_racecenter_etappes_tdf_2026_2026-11-08.json

| | |
|---|---|
| **Adres** | https://racecenter.letour.fr/api/stage-2026?xdt=245feyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9eyJrc3AiOiJNMkkwWVRZeE1EVXlNRFF4IiwiaWF0IjoxNzk0MTMzOTAxfQQcqyCHcV9Knpl1OrYMDDpEjRg9z1eEz5DhM8xf4hu1c |
| **Opgehaald** | 2026-11-08T10:40:20.965Z (UTC) = 2026-11-08T11:40:20+01:00 (Amsterdam). Server-`Date`: Sun, 08 Nov 2026 10:31:41 GMT |
| **Antwoord** | HTTP 200, `application/json; charset=utf-8` |
| **Grootte** | 167,386 bytes |
| **SHA-256** | `af3882235dbe5e6e0cf52f6d5a358bc3964b35a392ce6b1453a1ff089e50e552` |

## Methode
XHR-respons. De racecenter-pagina (https://racecenter.letour.fr/en/) haalde dit adres zelf op bij het laden in de ingebouwde browser (oorspronkelijk geladen 2026-11-08T10:31:41Z volgens de `Date`-header). De respons is daarna uit de browsercache gelezen met `fetch(url, {cache: 'only-if-cached'})`, dus zonder nieuw verzoek, en ongewijzigd weggeschreven (SHA-256 gecontroleerd). Ik heb het `xdt`-token níet zelf hergebruikt in curl of in een nieuw verzoek.

## Inhoud in de ruwe bron?
Nvt (JSON-respons). De racecenter-HTML zelf is een JavaScript-app; ik heb die HTML niet als fixture opgeslagen.

## Velden
Lijst van 21 etappe-objecten met: `stage` (1-21), `date` (`2026-07-26T00:00:00+02:00`), **`startTime`** (`"17:50:00"`), **`endTime`** (`"19:46:00"`), **`timezone`** (`"Europe/Paris"`), `length` (`88.7`), `lengthDisplay` (`89`), `type` (`HMG`×8, `PLN`×7, `VAL`×4, `EQU`×1, `PAS`×1), `isCancelled`, `departureCity`/`arrivalCity` (`label`, `code`, `id`, `content.texts` met Franse HTML-tekst en afbeelding), plus interne velden `_id`, `_key`, `_bind`, `_parent`, `_updatedAt`, `podiumDisplayMode`, `showGroups`.

## Bijzonderheden
- De lijst is **niet gesorteerd** (volgorde begint met 4, 1, 20, 8, 9, 6).
- Vermoeden over de typecodes: `PLN` vlak, `VAL` heuvelachtig, `HMG` hooggebergte, `EQU` ploegentijdrit, `PAS`? (niet zeker).
- Teksten bij steden zijn HTML-fragmenten met `<br />`, in het Frans.
- Het racecenter toont buiten de Tour de laatste etappe (21) van 2026.
