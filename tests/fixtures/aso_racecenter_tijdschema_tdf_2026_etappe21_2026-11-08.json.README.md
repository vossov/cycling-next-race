# aso_racecenter_tijdschema_tdf_2026_etappe21_2026-11-08.json

| | |
|---|---|
| **Adres** | https://racecenter.letour.fr/api/checkpointList-2026-21?xdt=245feyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9eyJrc3AiOiJOR00zT0RBM1pqUTRZVEJqIiwiaWF0IjoxNzk0MTMzOTAxfQ5_PumOnUcAp9-wCoeJBTsDbTEpC1kdE1nuXgVrX2FZ8 |
| **Opgehaald** | 2026-11-08T11:15:08.854Z (UTC) = 2026-11-08T12:15:08+01:00 (Amsterdam) |
| **Antwoord** | HTTP 200, `application/json; charset=utf-8` |
| **Grootte** | 11,166 bytes |
| **SHA-256** | `eb48b5f92194ca7c26b1374d80f6db579a5392db750c391d01eac49f02ab89a2` |

## Methode
Respons die de racecenter-pagina (https://racecenter.letour.fr/en/) zelf ophaalde bij het laden om 10:31Z; daarna uit de browsercache gelezen met `fetch(url, {cache: 'only-if-cached'})`, dus zonder nieuw verzoek. SHA-256 gecontroleerd.

## Inhoud in de ruwe bron?
Nvt (JSON, adres `api/checkpointList-2026-21?xdt=…`).

## Velden
19 checkpoints met: `checkpoint`, `place`, `road`, `length` (km), `latitude`/`longitude`, **`lowSchedule` / `middleSchedule` / `highSchedule`** (passeertijden bij drie snelheden, `"17:59:00"`), `caravanSchedule`, `checkpointTypes[]` (`{type: sprint|real|fictive, code, number}`), `checkpointSummits[]`, **`checkpointMeteo`** (temperatuur, wind, weeromschrijving, tijdstip), `country`, `countryCode`, `photoFinish`, `updatedAt`.

## Bijzonderheden
- **Het officiële tijdschema** als data, precies wat `stage-{n}-times.htm` bij cyclingstage moest leveren. Inclusief de tussensprint (`PARIS - HAUT DES CHAMPS-ÉLYSÉES (5E PASSAGE)`, km 27,9).
- Tijden zonder tijdzone; de etappelijst geeft `timezone: Europe/Paris`.
- Plaatsnamen in hoofdletters en in het Frans; ook regels als `2e passage sur la ligne d'arrivée`.
- Het `xdt`-token is niet zelf hergebruikt.
