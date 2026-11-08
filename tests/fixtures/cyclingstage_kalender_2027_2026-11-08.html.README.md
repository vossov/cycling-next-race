# cyclingstage_kalender_2027_2026-11-08.html

| | |
|---|---|
| **Adres** | https://www.cyclingstage.com/uci/cycling-calendar-2027/ |
| **Opgehaald** | 2026-11-08T12:19:12+01:00 |
| **Antwoord** | HTTP 200, `text/html; charset=utf-8` |
| **Grootte** | 49,859 bytes |
| **SHA-256** | `7b680b33e9e72c2c43f1f11599e7e9f5a5a64e0fc5f2177d823774b719dc1891` |

## Methode
curl met `--compressed`, `Accept-Language: nl,en;q=0.8` en user-agent `Mozilla/5.0 (compatible; cycling-next-race-research/2026-11; +https://github.com/vossov/cycling-next-race)`. De body is ongewijzigd opgeslagen.

## Inhoud in de ruwe bron?
Ja. Gezocht op "Tour Down Under" en "UAE Tour": gevonden.

## Velden
Per maand een tabel *Date | Race | Country | Route | Results*: dagen (`19-24`, zonder maand of jaar in de cel), koersnaam, land (voluit: `Australia`, `UAE`, `Spain`), en lege kolommen Route en Results.

## Bijzonderheden
- Dit is exact het adres dat de integratie zelf bouwt (`KALENDER_URL = BASIS + "/uci/cycling-calendar-{y}/"` in `cyclingstage.py`). CLAUDE.md zegt dat hij op 25 september 2026 nog niet bestond; **op 8 november 2026 bestaat hij** (59 tabelrijen).
- Route- en uitslagkolommen zijn nog leeg, dus nog geen routeadressen.
- Gevonden via de menulinks op de Giro-routepagina (die linkt ook naar `/giro-2027-route`, `/tour-de-france-2027-route`, `/vuelta-2027-route`, `/tour-de-france-femmes-2027`, `/world-championships-2027-france`).
