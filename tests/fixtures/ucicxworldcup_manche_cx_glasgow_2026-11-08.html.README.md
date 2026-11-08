# ucicxworldcup_manche_cx_glasgow_2026-11-08.html

| | |
|---|---|
| **Adres** | https://www.ucicyclocrossworldcup.com/en/calendar/2026-2027/glasgow |
| **Opgehaald** | 2026-11-08T20:38:36+01:00 |
| **Antwoord** | HTTP 200, `text/html; charset=UTF-8` |
| **Grootte** | 62020 bytes |
| **SHA-256** | `6d4e94e9fdc774a15b18bfa203af1f1fd58c3c6f5e27a7455bf62b44020e0103` |

## Methode
curl met `--compressed`, `Accept-Language: nl,en;q=0.8` en user-agent `Mozilla/5.0 (compatible; cycling-next-race-research/2026-11; +https://github.com/vossov/cycling-next-race)`, vanuit de Claude-omgeving (die bereikt deze sites rechtstreeks; Cowork was niet nodig). De body is ongewijzigd opgeslagen. robots.txt van beide hosts op dezelfde dag nagelezen: alleen `Disallow: /public/`.

## Inhoud in de ruwe bron?
Ja. `Programme`: `Women Elite 12:40`, `Men Elite 14:10`. Vlag `alt="United Kingdom"`. Datum als "Sunday 13 December 2026" (Engels; `_NL_DATUM` leest hem niet, net als bij Ostrava).

## Bijzonderheden
- **De pagina zegt "local time in Glasgow (GMT +1)".** Glasgow zit op 13 december op GMT (UTC+0), niet op GMT+1. Met `LAND_ZONE` → Europe/London wordt 12:40 / 14:10 bij ons 13:40 / 15:10 — precies de vaste tv-tijden van de vrouwen- en mannenelite bij de andere manches (Benidorm: 13:40 / 15:10 CET). Dat pleit ervoor dat de tijden echt GMT zijn en "+1" een vergissing van de site is. Niet zeker.
- **Geen zenders** ("Broadcasters" ontbreekt). Vijf weken voor de manche; Ostrava had ze op 8 november ook nog niet.
- Alleen de elite in het programma, geen jeugd.
