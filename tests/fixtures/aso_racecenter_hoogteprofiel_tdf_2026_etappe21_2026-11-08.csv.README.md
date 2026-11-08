# aso_racecenter_hoogteprofiel_tdf_2026_etappe21_2026-11-08.csv

| | |
|---|---|
| **Adres** | https://racecenter.letour.fr/profils/2026/profile-21-tiny-c039761a4e729cd2c42426cebe111b52.csv |
| **Opgehaald** | 2026-11-08T11:15:02.187Z (UTC) = 2026-11-08T12:15:02+01:00 (Amsterdam) |
| **Antwoord** | HTTP 200, `text/csv; charset=UTF-8` |
| **Grootte** | 47,069 bytes |
| **SHA-256** | `8c3e1129ed28d8162fabb77888c36d968a9d05b90f2d9571a6147398e0e8a93f` |

## Methode
Respons die de racecenter-pagina (https://racecenter.letour.fr/en/) zelf ophaalde bij het laden om 10:31Z; daarna uit de browsercache gelezen met `fetch(url, {cache: 'only-if-cached'})`, dus zonder nieuw verzoek. SHA-256 gecontroleerd.

## Inhoud in de ruwe bron?
Nvt (CSV, `text/csv`, `cache-control: public, max-age=2592000`).

## Velden
Kolommen (`;`-gescheiden): `latitude;longitude;altitude;azimuth;slope;dvdone;dvrest;kmdone;kmto;cpnumero;cptype;sumcategory`.
888 punten, één per **100 m** (km 0 → 88,7), hoogte 32,2–126,5 m. `cptype`: `real` (start), `sprint`, `summit` (3×), `arrival`. **`sumcategory`**: officiële colcategorie (hier 3× `4`). `dvdone`/`dvrest` = gedane/resterende hoogtemeters.

## Bijzonderheden
- **Alternatief voor het hoogteprofiel** voor de ASO-koersen, mét officiële colcategorieën en met de plek van de tussensprint. Dat zijn precies twee open punten in CLAUDE.md (colcategorie als schatting, tussensprint).
- Het adres bevat **geen `xdt`-token**, wel een hash: `profils/2026/profile-21-tiny-c039761a4e729cd2c42426cebe111b52.csv`. Die hash staat niet in de etappelijst (`stage-2026`); waar hij vandaan komt is onbekend.
- `tiny` suggereert een grovere versie; of er een fijnere bestaat is niet onderzocht.
- Dekt alleen ASO-koersen (zie CLAUDE.md: Tour, Vuelta, Dauphiné, Parijs-Nice, Roubaix, Luik, Flèche, TdF Femmes).
