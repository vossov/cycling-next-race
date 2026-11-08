# ucicxworldcup_uitslagen_cx_2026-11-08.html

| | |
|---|---|
| **Adres** | https://www.ucicyclocrossworldcup.com/en/results |
| **Opgehaald** | 2026-11-08T20:38:35+01:00 |
| **Antwoord** | HTTP 200, `text/html; charset=UTF-8` |
| **Grootte** | 1257311 bytes |
| **SHA-256** | `616757b94284525f2775d6d77c80815b02c0eccc077a5f63270b21fbeae0d9b6` |

## Methode
curl met `--compressed`, `Accept-Language: nl,en;q=0.8` en user-agent `Mozilla/5.0 (compatible; cycling-next-race-research/2026-11; +https://github.com/vossov/cycling-next-race)`, vanuit de Claude-omgeving (die bereikt deze sites rechtstreeks; Cowork was niet nodig). De body is ongewijzigd opgeslagen. robots.txt van beide hosts op dezelfde dag nagelezen: alleen `Disallow: /public/`.

## Inhoud in de ruwe bron?
Ja. Geen manche van 2026-2027 (Ostrava is pas op 27 november), wel de seizoenen 2025-2026, 2024-2025 en ouder: per manche een accordeon met plaats, datum (`23/11/25`) en per categorie het podium met tijd of achterstand, plus een PDF met de volledige uitslag.

## Wat dit vaststelt
- Dezelfde opmaak als de uitslagenpagina van de Superprestige (`accordion--uitslagen-*`, `<h3>Women Elite :</h3>`, `rankings-top-3-time`), met één verschil: **de plaats staat in een `<p>`, niet in een `<h2>`**. `parse_sp_uitslagen` knipt de plaats af op `</h2>` en krijgt hier de hele manche als "plaats"; de categorieën en podia leest hij wél goed. Daardoor geeft `podium(..., plaats="Benidorm", ...)` een lege lijst.
- Categorieën heten in het Engels (`Women Elite`, `Men Elite`); `is_elite` herkent ze.
- Sommige categorieën dragen `(no World Cup)`.

## Niet vastgesteld
Hoe de pagina eruitziet zodra er een manche van het nieuwe seizoen op staat. Vermoedelijk komt 2026-2027 bovenaan in dezelfde vorm, maar dat is pas na 27 november te zien.
