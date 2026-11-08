# Wat de integratie met deze data zou kunnen aanvullen

Opgesteld op 8 november 2026, na het lezen van `vossov/cycling-next-race` (commit `6682525`, v0.31.5): `CLAUDE.md` (open punten, bronnen), `docs/gevraagde-paginas.md` en `docs/robots/`. Ik heb niets aan de repo veranderd.

Elke regel noemt het bewijsbestand in `tests/fixtures/` van deze zip. Wat een vermoeden is, staat er zo bij. De robotsregel van het project ("wat niet expliciet verboden is, mag") is gevolgd. Waar die voor ClaudeBot iets anders zegt dan voor de user-agent van de integratie, staat dat erbij.

## 0. Eerst dit: de robots.txt van wielerflits is veranderd

`docs/robots/wielerflits.nl.txt` in de repo (7 september 2026) noemt ClaudeBot niet. Vandaag (8 november) staat er wel:

```
User-Agent: ClaudeBot
Disallow: /
```

met dezelfde regel voor GPTBot, CCBot, Google-Extended, Applebot-Extended, meta-externalagent en Bytespider. Voor `User-Agent: *` staat er nu ook `Allow: *` en er zijn regels bijgekomen (`/wielerkalender/*?*country=`, `/api/bff/`, `/oidc/` …). De tv-gids `/nieuws/wielrennen-op-tv/` valt voor `*` nog onder geen enkele regel.

- **Voor de integratie** (eigen user-agent, geen ClaudeBot) verandert er volgens de projectregel niets.
- **Voor ontwikkelwerk met Claude** betekent het wel iets: Claude haalt wielerflits niet meer op. Fixtures moeten dan met de hand komen, of uit een andere bron.
- Werk `docs/robots/wielerflits.nl.txt` en de paragraaf "Wat de robots.txt van onze bronnen zegt" bij. Het nieuwe bestand staat in deze zip als `docs/robots/www.wielerflits.nl.txt`.

De robots.txt van cyclingstage is **niet** veranderd (alleen witruimte), zie `docs/robots/www.cyclingstage.com.txt`.

## 1. Open punten uit CLAUDE.md en `gevraagde-paginas.md`

| open punt in de repo | wat ik vond | bewijs | wat het oplevert |
|---|---|---|---|
| **Tijdschema / tussensprint** (2.2): `stage-{n}-times.htm` is "het laatste met de hand geraden adres" | Het tijdschema bestaat bij cyclingstage, maar als **JPG**: `/images/giro-italy/2026/stage-14-times.jpg`. De etappepagina **linkt er zelf naar** (titel "timings"). Het is de officiële RCS-cronotabella, met tussensprint, cols en passeertijden bij 34/32/30 km/u. | `cyclingstage_giro_2026_etappe14_2026-11-08.html`, `cyclingstage_giro_2026_etappe14_tijdschema_2026-11-08.jpg` | Het `.htm`-pad kan weg (er is nu bewijs dat het formaat `.jpg` is). Uitlezen kan alleen met OCR. Dat is zwaar voor HA en foutgevoelig, dus niet aan te raden. |
| idem | De etappetekst zegt bij de Giro: "intermediate sprint at **kilometre 116.0**". | idem | Leesbaar als regex. **Maar:** op de cronotabella is km 116,0 de **Red Bull-kilometer**; de echte tussensprint ligt op km 53,9. De tekst is dus niet betrouwbaar als "tussensprint". |
| idem, ASO-koersen | De racecenter-API `checkpointList-{jaar}-{etappe}` is het **officiële tijdschema als JSON**: plaats, km, passeertijd bij drie snelheden, type (`sprint`), karavaan en het **weer per punt**. | `aso_racecenter_tijdschema_tdf_2026_etappe21_2026-11-08.json` | Tussensprint en schema voor acht ASO-koersen, zonder te raden. Kanttekening: elk API-adres draagt een `xdt`-token (zie §3). |
| **Colcategorie is een schatting** (`_cat_from_score`) | ASO-profiel-CSV heeft per punt `cptype` (`summit`, `sprint`) en **`sumcategory`** (officiële categorie). | `aso_racecenter_hoogteprofiel_tdf_2026_etappe21_2026-11-08.csv` | Officiële categorieën vóór de koers, voor ASO-koersen. |
| idem, na de koers | CyclingFlash zet in de uitslagpagina `intermediatePoints` met per col `name`, `kmMarker`, `category` en punten. | `cyclingflash_uitslag_weg_vuelta_etappe14_2026-11-08.html` | Officiële categorie per col, maar alleen gezien **na** de etappe. Of het er vooraf staat, is niet onderzocht. |
| **Hoogteprofiel** (nu cyclingstage-GPX) | Alternatieven: (a) ASO-CSV, één punt per 100 m met hoogte, helling, km gedaan/te gaan, hoogtemeters gedaan/te gaan, cols en sprint. (b) CyclingFlash: per etappe een **SVG-pad** (genormaliseerd mini-profiel, geen meters) plus `elevationGain`, `climbsCount`, `finalKmGradient`, `overallProfile`/`finishProfile`. (c) Domestique "Profile": **niets**, alleen tekst. (d) TNT, UCI, Velora: geen profiel gezien. | `aso_racecenter_hoogteprofiel_…csv`, `cyclingflash_etappe_weg_vuelta_etappe14_2026-11-08.html`, `domestiquecycling_profiel_weg_il_lombardia_2026-11-08.html` | ASO-CSV is een volwaardige vervanger voor ASO-koersen. Het CyclingFlash-SVG is alleen geschikt voor de kleine profieltjes in "Komende dagen", en dan als tekening, niet als data. Het adres van de ASO-CSV bevat een hash die niet in de etappelijst staat; waar die vandaan komt is nog onbekend. |
| **Tijdzones ACDT/GST** ontbreken in `TIJDZONES` | CyclingFlash geeft starttijd en verwachte finish (snel/langzaam) als **UTC** (`"start":"2026-09-05T11:33:00Z"`). ASO geeft een tijdzonenaam (`"timezone":"Europe/Paris"`). | `cyclingflash_etappe_weg_vuelta_etappe14_2026-11-08.html`, `aso_racecenter_etappes_tdf_2026_2026-11-08.json` | Met UTC uit de bron is de afkortingstabel voor die koersen niet nodig. |
| **Buiten het seizoen staat er niets** (kalender 2027 bestond 25 sep nog niet) | CyclingFlash heeft de **kalender 2027** al (januari 2027: 20 koersen, Tour Down Under met startlijstlink). De UCI-JSON loopt t/m april 2028. | `cyclingflash_kalender_weg_2027_men_elite_januari_2026-11-08.html`, `uci_kalender_upcoming_2026-11-08.json` | De aftelweergave kan doorlopen naar januari. **En belangrijker: de eigen bron van de integratie heeft hem ook.** `https://www.cyclingstage.com/uci/cycling-calendar-2027/` (precies `KALENDER_URL` met `y=2027`) bestaat op 8 november 2026, met koersen vanaf de Tour Down Under (19–24 januari) maar nog zonder routes en uitslagen. Bewijs: `cyclingstage_kalender_2027_2026-11-08.html`. De integratie kan dus nu al vooruitkijken naar 2027 in plaats van tot 1 januari "Seizoen afgelopen" te tonen. |
| **WK vrouwen: eigen GPX?** | Ja: `cdn.cyclingstage.com/images/wk-wielrennen/2026/route-women.gpx`. | `cyclingstage_wk_2026_route_wegrit_vrouwen_2026-11-08.html` | `_profiel_past` hoeft dit profiel niet te weigeren. |
| **Klassementspagina's** (4.4) | Staan er nu: top 5 plus de leider na elke etappe. | `cyclingstage_vuelta_2026_puntenklassement_…`, `…_bergklassement_…` | Punten- en bergklassement terug, al is het alleen de top 5. Volledige standen per rit: CyclingFlash (`/result/stage-N/points`, `/mountain`, `/youth`; links gezien, niet opgehaald). |
| **Uitvallerspagina** (4.3) | Per etappe `DNF stage N` / `DNS stage N` met rugnummer, naam, land, ploeg. Geen tijdstip. | `cyclingstage_vuelta_2026_uitvallers_2026-11-08.html` | Etappe van uitval (beter dan het onbetrouwbare tijdstempel van de startlijst). Landcodes zijn eigen afkortingen (`slo`, `spa`). |
| **Tour of Britain: etappe- en uitslagpagina's** (2.3, 3.4) | De adressen in `gevraagde-paginas.md` geven **404**, en de koers- en routepagina linken naar geen enkele etappe- of uitslagpagina. | `cyclingstage_tour_of_britain_2026_koers_2026-11-08.html` (de 404's zijn niet als fixture bewaard) | Voor zulke koersen heeft cyclingstage geen uitslag. Terugval: CyclingFlash of Domestique (uitslag Lombardia als voorbeeld). |
| **Vrouwenkoers en niet-Vuelta-etappe** (3.3, 3.4) | Ronde van Vlaanderen vrouwen (koers en route) en Giro-route plus etappe 14 opgeslagen. GPX-namen: `tour-of-flanders/2026/route-women.gpx` (niet `route.gpx`), `giro-italy/2026/stage-14-parcours.gpx`. Giro-etappes: `/giro-2026-route/stage-N-italy-2026/`. | `cyclingstage_ronde_van_vlaanderen_vrouwen_2026_…`, `cyclingstage_giro_2026_…` | De GPX-patronen in CLAUDE.md missen `route-women.gpx` voor eendaagse vrouwenkoersen. Op deze (na afloop bijgewerkte) etappepagina's stond **geen start- of finishtijd** in de tekst. |
| **Favorieten** (4.2) | CyclingFlash zet per etappe "Win chance" in procenten. | `cyclingflash_etappe_weg_vuelta_etappe14_2026-11-08.html` | Een gepubliceerde voorspelling van CyclingFlash, geen waarneming. Alleen te gebruiken als het zo genoemd wordt. |
| **Live** | `secure.tourtrackerdata.com` (de RCS-tracker die cyclingstage bij de Giro inbedt) heeft `User-agent: *` / `Disallow: /`, dus **verboden**. De ASO-racecenter laadt `telemetryCompetitor-2026` en `telemetryPack-2026-21`; de inhoud buiten koerstijd heb ik niet bekeken. | `docs/robots/secure.tourtrackerdata.com.txt`, lijst in het rapport §4 (C7) | Geen nieuwe live-bron. ASO blijft de enige kandidaat, zoals CLAUDE.md al zegt. |
| **ASO-robots.txt "nog niet nagekeken"** | `racecenter.letour.fr/robots.txt` → 302 naar een HTML-pagina, dus **geen robots.txt**. `www.letour.fr` verbiedt `/api`, maar dat is een andere host. | `docs/robots/www.letour.fr.txt`, rapport §1 | Volgens de projectregel toegestaan. `racecenter.lavuelta.es` heb ik vandaag niet opnieuw bekeken (de repo noemt een 404 op 7 september). |

## 2. Nieuwe dingen die er nu nog niet in zitten

| idee | bron | bewijs | kanttekening |
|---|---|---|---|
| **Cyclocross** als extra niveau | CyclingFlash (kalender per maand, uitslag, starttijden in UTC, series), officiële seriesites (starttijden), wereldbekersite | rapport §3 | CyclingFlash zit achter Cloudflare (curl kreeg 403). De seriesites werken met curl. |
| Starttijden per categorie bij cross | Superprestige-manchepagina, wereldbeker-manchepagina, Velora | `superprestige_manche_cx_niel_…`, `ucicxworldcup_manche_cx_ostrava_…`, `veloracycling_koers_cx_…` | CyclingFlash had de juniorentijden van Niel omgedraaid; neem de organisator als waarheid. |
| Officiële crossuitslag met rugnummer en UCI-id | Superprestige-PDF | `superprestige_uitslag_cx_overijse_men_elite_2026-11-08.pdf` | PDF uitlezen in HA vraagt een extra pakket. |
| **Weer onderweg** | ASO `checkpointMeteo` per checkpoint | `aso_racecenter_tijdschema_…json` | Alleen ASO-koersen. |
| Verwachte finish (snel/langzaam) | CyclingFlash `finishExpectedFast/Slow` | `cyclingflash_etappe_weg_vuelta_etappe14_…` | De integratie heeft al één finishtijd (0.31.4); dit is een tweede bron om te vergelijken. |
| **Geslacht en UCI-klasse als eigen veld**, met jaar in de datum | Domestique-kalender | `domestiquecycling_kalender_weg_2026_2026-11-08.html` | Geen cross. Ongesorteerde "Upcoming"-lijst. Bruikbaar als terugval voor de kalender (met curl bereikbaar). |
| Tv-zenders per land, zonder parse op vlaggen | CyclingFlash tv-gids (`countryCodes` per uitzending, tijden in UTC) | `cyclingflash_tvgids_2026-11-08.html` | CyclingFlash levert volgens CLAUDE.md de data aan wielerflits. Vermoeden: zelfde gegevens, nu als JSON. Cloudflare-kanttekening geldt. |

## 3. Wat niet gaat

- **ProCyclingStats, FirstCycling, cyclocross24**: robots.txt sluit ClaudeBot uit (PCS ook `Claude-User`, FirstCycling iedereen).
- **tourtrackerdata.com**: `Disallow: /` voor iedereen.
- **ASO-API buiten de browser**: elk adres onder `/api/` draagt `?xdt=<token>`. Of de API zonder token antwoordt, heb ik **niet** getest, want ik heb dat token niet zelf gebruikt. De profiel-CSV heeft geen token, alleen een hash in de bestandsnaam. Of de integratie die hash zonder browser kan vinden, is onbekend.
- **CyclingFlash vanuit Home Assistant**: niet getest. curl met een eerlijke user-agent kreeg 403 (Cloudflare). CLAUDE.md beschrijft hetzelfde bij ProCyclingStats, inclusief het mislukken van cloudscraper en curl_cffi. Verwacht hier hetzelfde (vermoeden).

## 4. Voorgestelde volgorde (alleen op basis van wat er nu ligt)

1. `docs/robots/wielerflits.nl.txt` bijwerken en de wielerflits-paragraaf herzien (§0).
2. Het `times.htm`-pad vervangen door de wetenschap dat het `times.jpg` is, en `_fetch_times`/`_parse_times`/`sprints` weghalen zoals CLAUDE.md voorstelt. Er is nu bewijs.
3. Na Parijs-Tours ook de kalender van het volgende jaar ophalen (bestaat al bij cyclingstage, zie §1).
4. GPX-patroon `route-women.gpx` erbij, en het WK-vrouwenprofiel niet meer weigeren.
5. Punten- en bergklassement (top 5) en uitvallers van cyclingstage inlezen: zelfde host, geen nieuwe bron.
6. ASO-bron in `bronnen.py`: etappelijst, tijdschema (tussensprint, officieel schema) en profiel-CSV (officiële colcategorie). Eerst uitzoeken of de API zonder `xdt` antwoordt en waar de CSV-hash vandaan komt.
7. Pas daarna: CyclingFlash als bron (cross, 2027, UTC-tijden). Alleen als een test vanuit HA laat zien dat Cloudflare het toelaat.
