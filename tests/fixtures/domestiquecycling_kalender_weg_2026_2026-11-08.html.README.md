# domestiquecycling_kalender_weg_2026_2026-11-08.html

| | |
|---|---|
| **Adres** | https://www.domestiquecycling.com/en/cycling-races/2026/ |
| **Opgehaald** | 2026-11-08T11:58:54+01:00 |
| **Antwoord** | HTTP 302, `text/html; charset=UTF-8` |
| **Grootte** | 1,025,504 bytes |
| **SHA-256** | `25c2b39b8dbbfde25d1d923b45e64ebe50a9f1f1c7c8cfb4e74c0420c4e77672` |

## Methode
curl met `--compressed`, `Accept-Language: nl,en;q=0.8` en user-agent `Mozilla/5.0 (compatible; cycling-next-race-research/2026-11; +https://github.com/vossov/cycling-next-race)`. De body is ongewijzigd opgeslagen.

## Inhoud in de ruwe bron?
Ja. Gezocht op "Tour du Faso" en "Tour de Okinawa": gevonden.

## Velden
Drie tabellen *Current races*, *Upcoming* en *Finished* met kolommen *Date | Race | Gen | Cat | Leader/Winner*:
- datum **met jaar** (`30.10.2026 - 08.11.2026` of `08.11.2026`)
- koers (link `/en/cycling-races/{slug}/2026/`)
- **geslacht** als eigen kolom (`Men` / `Women`)
- UCI-klasse (`2.UWT`, `2.WWT`, `1.Pro`, `2.Pro`, `2.2` …)
- leider (lopende ronde) of winnaar (link `/en/riders/{slug}/`)
Ongeveer 500 koerslinks op één pagina (heel 2026).

## Bijzonderheden
- Het adres `/en/cycling-races/2026/` stuurt door (301) naar `/en/cycling-races/`.
- *Upcoming* is niet op datum gesorteerd (11.12 vóór 01.12).
- Geen cross (alleen weg).
- Rennerspagina's (`/en/riders/`) zijn voor Bingbot verboden in robots.txt; voor `*` niet.
