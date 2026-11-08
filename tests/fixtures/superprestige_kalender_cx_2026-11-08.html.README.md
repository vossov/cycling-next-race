# superprestige_kalender_cx_2026-11-08.html

| | |
|---|---|
| **Adres** | https://www.superprestigecyclocross.be/nl/kalender |
| **Opgehaald** | 2026-11-08T20:38:33+01:00 |
| **Antwoord** | HTTP 200, `text/html; charset=UTF-8` |
| **Grootte** | 73772 bytes |
| **SHA-256** | `d0d1036d3b49d4e84960ff6963a3a6e44ca52698a14710a7497b66be9deecbaf` |

## Methode
curl met `--compressed`, `Accept-Language: nl,en;q=0.8` en user-agent `Mozilla/5.0 (compatible; cycling-next-race-research/2026-11; +https://github.com/vossov/cycling-next-race)`, vanuit de Claude-omgeving (die bereikt deze sites rechtstreeks; Cowork was niet nodig). De body is ongewijzigd opgeslagen. robots.txt van beide hosts op dezelfde dag nagelezen: alleen `Disallow: /public/`.

## Inhoud in de ruwe bron?
Ja. Acht `competition-block`s: zes komende manches (Niel 11/11, Merksplas 14/11, Ruddervoorde 06/12, Heusden-Zolder 25/12, Diegem 30/12, Gullegem 02/01/27) en twee gereden (Overijse 25/10, Middelkerke 05/11), elk met datum, plaats, vlag (`alt="België"`) en een link naar `/nl/kalender/2026-2027/{plaats}`.

## Wat dit vaststelt
- `SP_KALENDER_URL` (`/nl/kalender`) **klopt**; tot nu toe was dat een aanname.
- `parse_fc_kalender` leest de pagina zonder aanpassing: 8 manches.
- De gereden manches staan **ná** de komende (eigen blok "Past races"), niet op datum.
- Gullegem staat met hoofdletter in het adres (`/2026-2027/Gullegem`).
