# aso_racecenter_klassement_tdf_2026_etappe21_2026-11-08.json

| | |
|---|---|
| **Adres** | https://racecenter.letour.fr/api/rankingType-2026-21?xdt=245feyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9eyJrc3AiOiJaVFZsTWpBellUTmhORGt5IiwiaWF0IjoxNzk0MTMzOTAxfQgTYJwFTxSUvRHDfbVj61D3pOsHhjzfIrJq7yFYjxTUw |
| **Opgehaald** | 2026-11-08T10:40:45.730Z (UTC) = 2026-11-08T11:40:45+01:00 (Amsterdam). Server-`Date`: Sun, 08 Nov 2026 10:31:41 GMT |
| **Antwoord** | HTTP 200, `application/json; charset=utf-8` |
| **Grootte** | 343,892 bytes |
| **SHA-256** | `70ae79d6952a437fc185b3155e1232aec8242799a42183fd8d60ac1003ef9dda` |

## Methode
XHR-respons. De racecenter-pagina (https://racecenter.letour.fr/en/) haalde dit adres zelf op bij het laden in de ingebouwde browser (oorspronkelijk geladen 2026-11-08T10:31:41Z volgens de `Date`-header). De respons is daarna uit de browsercache gelezen met `fetch(url, {cache: 'only-if-cached'})`, dus zonder nieuw verzoek, en ongewijzigd weggeschreven (SHA-256 gecontroleerd). Ik heb het `xdt`-token níet zelf hergebruikt in curl of in een nieuw verzoek.

## Inhoud in de ruwe bron?
Nvt (JSON-respons).

## Velden
Lijst van 213 objecten, twee soorten:
- **22 klassementsrecords**: `type` (codes `ite`, `itg`, `ipe`, `ipg`, `img`, `ime`, `ije`, `ijg`, `ete`, `etg`, `ice`, `icg`, `iqe`, `iqg`), `checkpoint`, `length`, `status`, `rankings[]` met `position`, `bib`, `absolute` (ms, bijv. `7129000`), `relative`, `bonus`, `penality`, `$rider` (verwijzing `allCompetitors-2026:{hash}`)
- **191 checkpointrecords**: `checkpoint`, `place`, `latitude`, `longitude`, `length`, `lowSchedule`/`middleSchedule`/`highSchedule`, `checkpointMeteo`, `checkpointTypes`, `checkpointSummits`, `road`

## Bijzonderheden
- **Rennersnamen staan níet in dit bestand**, alleen rugnummer en een verwijzing naar `allCompetitors-2026` (een ander endpoint, niet opgehaald).
- Tijden in milliseconden.
- Typefout in de bron: `penality`.
- Vermoeden over de codes: eerste letter `i` individueel / `e` ploeg, middelste letter `t` tijd, `p` punten, `m` berg, `j` jongeren, `c` strijdlust, `q`?, laatste letter `e` etappe / `g` algemeen. Grote lijsten: `ite`/`itg` 158 renners, `ipg` 120, `img` 59, `ije`/`ijg` 35, `ete`/`etg` 23 ploegen.
- Het racecenter laadde ook `rankingType-2026-20` en `rankingTypeJerseys-2026-22` (een etappe 22 bestaat niet in de etappelijst).
