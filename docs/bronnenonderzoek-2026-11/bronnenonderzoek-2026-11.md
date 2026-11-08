# Bronnenonderzoek cycling-next-race, november 2026

Uitgevoerd op zondag 8 november 2026, tussen 11:13 en 12:02 (Amsterdam). Ronde 1 (11:13–11:41) volgde de opdracht. Ronde 2 (11:50–12:02) was een aanvullende webzoektocht naar andere bronnen; die bestanden en hosts zijn hieronder gemarkeerd met **(ronde 2)**. Ronde 3 (12:05–12:20) ging uit van de repo zelf: de open punten in `CLAUDE.md` en `docs/gevraagde-paginas.md`, plus alternatieven voor het hoogteprofiel. Die bestanden zijn gemarkeerd met **(r3)**. De vertaling naar concrete aanvullingen voor de integratie staat apart in **`docs/aanvullingen-voor-de-integratie.md`**. Alle opgeslagen pagina's staan in `tests/fixtures/`, met per bestand een `.README.md`. De robots.txt-bestanden staan letterlijk in `docs/robots/`.

Gebruikte clients:
- **curl** met user-agent `Mozilla/5.0 (compatible; cycling-next-race-research/2026-11; +https://github.com/vossov/cycling-next-race)`
- **de ingebouwde browser van de Claude-desktopapp** (Chromium 152, user-agent met `Claude/4.4212.0`), voor CyclingFlash (Cloudflare) en voor de XHR-adressen

Robots.txt is beoordeeld volgens de projectregel: wat niet expliciet verboden is, mag. De regels voor `User-agent: *` én voor `ClaudeBot` zijn op mij toegepast.

### 1. Robots.txt

| host | bestand opgeslagen | relevante regels (letterlijk) | oordeel voor onze paden |
|---|---|---|---|
| www.wielerflits.nl | `docs/robots/www.wielerflits.nl.txt` | `User-Agent: ClaudeBot` / `Disallow: /`. Voor `*`: `Allow: *`, `Disallow: /wielerkalender/*?*country=`, `Disallow: /wielerkalender/*?*classification=`, `Disallow: /*?*utm_source=`, `Disallow: /archief/*` | **ClaudeBot volledig uitgesloten, dus niets opgehaald.** Voor `*` zouden `/nieuws/veldrijden-op-tv/`, `/nieuws/wielrennen-op-tv/` en `/wielerkalender/...` wél mogen, zonder de query-filters `country`/`classification`. |
| wielerflits.be | `docs/robots/wielerflits.be.txt` (`/robots.txt` stuurt met 301 door naar `https://www.wielerflits.be/robots.txt`) | Gelijk aan .nl: `User-Agent: ClaudeBot` / `Disallow: /`, en voor `*` dezelfde regels met `/wielerkalender/*?*country=` en `/wielerkalender/*?*classification=` | **ClaudeBot volledig uitgesloten, dus niets opgehaald** (ook de wegkalender `/wielerkalender/road/...` niet). |
| sporza.be | `docs/robots/sporza.be.txt` | Groep met o.a. `User-agent: anthropic-ai`, `User-agent: ClaudeBot`, `User-agent: Claude-Web` → `Disallow: /`. Voor `*`: `Disallow: /libs/`, `/cm/`, `/etc/`, `/soccer/`, `/content/`, `/polopoly/`, `/permalink/`, `/sso/`, `/klassiekers/sso/`, `/*.app/$` | **ClaudeBot volledig uitgesloten, dus niets opgehaald.** Voor `*` zouden de `/nl/...`-artikelen en `/nl/categorie/...` wél mogen. |
| cyclingflash.com | `docs/robots/cyclingflash.com.txt` | `User-Agent: ClaudeBot`: `Disallow: /embed/`, `/oidc/`, `/api/bff/`, `/api/auth/`, `/api/webhooks/`, `/calendar/*?*country=`, `/calendar/*?*classification=`, `Crawl-delay: 10`. Voor `*` dezelfde Disallows plus `Allow: *`. | **Toegestaan** voor `/calendar/...`, `/event/...`, `/race/...`, `/serie/...`, `/tv-guide`. Niet toegestaan: de kalenderfilters `?country=` en `?classification=` (niet gebruikt). Crawl-delay van 10 s aangehouden. |
| www.tntsports.co.uk | `docs/robots/www.tntsports.co.uk.txt` | `User-agent: ClaudeBot` / `Crawl-delay: 1` (geen Disallow). Voor `*`: `Disallow: /*rss.xml`, `/*rss-flash.xml`, `/test/`, `/betting/go-`, `/betting/*/go-`. De Disallows op `*/2020/*/live*shtml` enz. gelden alleen voor `Googlebot`. | **Toegestaan** voor `/cycling/.../calendar-results.shtml`, `/cycling/.../live-*.shtml` en `/cyclo-cross/score-center.shtml`. |
| www.letour.fr | `docs/robots/www.letour.fr.txt` | `User-agent: *`: `Disallow: /admin`, `/sonatadmin`, `/api`, `/graphql`, `/login`, `/*/ajax`, `/*/block`, `/*/login`, `/*/sitemap`. Geen ClaudeBot-groep. | Niets van www.letour.fr opgehaald. `Disallow: /api` geldt alleen voor deze host, niet voor racecenter.letour.fr. |
| racecenter.letour.fr | — (bestaat niet) | `/robots.txt` geeft `HTTP 302` → `/en/not-found` (een HTML-pagina, status 200). Er is dus geen robots.txt. | Volgens de projectregel niets verboden; `/api/...` mag. |
| netsport.eurosport.io (extra: GraphQL-host achter TNT Sports) | — (bestaat niet) | `/robots.txt` geeft `HTTP 400` met `{"errors":[{"extensions":{"code":"INVALID_DOMAIN_HEADER"},"message":"\"domain\" header is missing"}]}` | Geen robots.txt, dus niets verboden. |
| cyclocross24.com **(ronde 2)** | `docs/robots/cyclocross24.com.txt` | `User-agent: ClaudeBot` / `Disallow: /` (ook `anthropic-ai`, `Claude-Web`). Voor `*`: `Content-Signal: search=yes,ai-train=no,use=reference`, `Allow: /`, later `Disallow: /*?*` | **ClaudeBot uitgesloten, dus niets opgehaald.** |
| www.procyclingstats.com **(ronde 2)** | `docs/robots/www.procyclingstats.com.txt` | `User-agent: ClaudeBot` / `Disallow: /` en `User-agent: Claude-User` / `Disallow: /` | **Uitgesloten, dus niets opgehaald.** |
| cx.procyclingstats.com **(ronde 2)** | `docs/robots/cx.procyclingstats.com.txt` | Gelijk aan www: `ClaudeBot` en `Claude-User` → `Disallow: /` | **Uitgesloten, dus niets opgehaald.** |
| firstcycling.com **(ronde 2)** | `docs/robots/firstcycling.com.txt` | `User-agent: ClaudeBot` / `Disallow: /` en `User-agent: *` / `Disallow: /` | **Uitgesloten (voor iedereen), dus niets opgehaald.** |
| www.superprestigecyclocross.be **(ronde 2)** | `docs/robots/www.superprestigecyclocross.be.txt` | `User-agent: *` / `Disallow: /public/` | Toegestaan voor `/nl/kalender/...`, `/nl/uitslagen`, `/nl/files/...` |
| x2otrofee.be **(ronde 2)** | `docs/robots/x2otrofee.be.txt` | `User-agent: *` / `Disallow:` (leeg = alles mag) | Toegestaan |
| www.ucicyclocrossworldcup.com **(ronde 2)** | `docs/robots/www.ucicyclocrossworldcup.com.txt` | `User-agent: *` / `Disallow: /public/` | Toegestaan voor `/en/calendar/...` |
| veloracycling.com **(ronde 2)** | `docs/robots/veloracycling.com.txt` | `User-Agent: *`: `Allow: /`, `Disallow: /api/`, `/admin/`, `/draft/`, `/go/`, `/preview/`. Groepen `Claude-Web` en `Anthropic-AI`: zelfde regels + `Crawl-delay: 2`. Geen ClaudeBot-groep. | Toegestaan voor `/races/...` |
| www.domestiquecycling.com **(ronde 2)** | `docs/robots/www.domestiquecycling.com.txt` | `User-agent: *`: `Allow: /`, `Disallow: /cpresources/`. `Bingbot`: `Disallow: /en/riders/` | Toegestaan voor `/en/cycling-races/...` |
| www.eurosport.nl **(ronde 2)** | `docs/robots/www.eurosport.nl.txt` | `User-agent: ClaudeBot` / `Crawl-delay: 1`; `*` zoals bij TNT (`/*rss.xml`, `/test/`, `/weddenschappen/go-`) | Toegestaan |
| www.uci.org **(ronde 2)** | `docs/robots/www.uci.org.txt` | `User-agent: *` / `Allow: /` | Toegestaan, ook `/api/calendar/upcoming` |
| www.cyclingstage.com **(r3)** | `docs/robots/www.cyclingstage.com.txt` (cdn.cyclingstage.com levert hetzelfde) | `#User-agent: *` / `#Disallow: /` **uitgecommentarieerd**; actieve groepen alleen voor andere bots (`MJ12bot` → `Disallow: /`, googlebot/bingbot enz. met o.a. `Disallow: /images`). Geen ClaudeBot. | Toegestaan. Ongewijzigd t.o.v. de repo-kopie van 7 september (alleen witruimte). |
| secure.tourtrackerdata.com **(r3)** | `docs/robots/secure.tourtrackerdata.com.txt` | `User-agent: *` / `Disallow: /` | **Verboden**, dus niets opgehaald. |
| en.wikipedia.org **(ronde 2)** | `docs/robots/en.wikipedia.org.txt` | Geen ClaudeBot-groep. `User-agent: *`: o.a. `Disallow: /w/` (dus ook `/w/api.php`) en diverse `/wiki/Special:`-paden | Toegestaan voor `/wiki/{artikel}` |

### 2. Opgeslagen pagina's

Alle bestanden staan in `tests/fixtures/`. De volledige adressen, tijdstippen en SHA-256-sommen staan in de bijbehorende README. CF = CyclingFlash. "Browser-fetch" betekent: paginabron via `fetch()` in de ingebouwde browser, SHA-256 gecontroleerd (zie §5 over curl en Cloudflare).

| bestand | adres | methode | inhoud in ruwe HTML? | velden | bijzonderheden |
|---|---|---|---|---|---|
| `cyclingflash_kalender_cx_men_elite_2026-11-08.html` | https://cyclingflash.com/calendar/cyclocross/2026-2027 | browser-fetch | ja (Niel, Oudenaarde) | datum `DD.MM`, koers + `/event/`-link, landvlag (afbeelding), klasse C1/C2/CN/CC, winnaar of startlijstlink | toont standaard Men Elite, november; 6 maandpagina's (9–2); `Turin International CyclocrossCancelled`; slugs met `-2`; event-slug ≠ race-slug |
| `cyclingflash_kalender_cx_women_elite_2026-11-08.html` | https://cyclingflash.com/calendar/cyclocross/2026-2027/women-elite/11 | browser-fetch | ja (Niel, Oudenaarde, Middelkerke) | idem | teller `44Races`, gelijk aan de mannen |
| `cyclingflash_event_cx_x2o_oudenaarde_2026-11-08.html` | https://cyclingflash.com/event/koppenbergcross-oudenaarde-2026 | browser-fetch | ja (Thibau Nys, Lucinda Brand) | land · plaats, aantal races, per categorie starttijd, links, top 3 met tijd/achterstand; in JSON `start` in UTC | 11:00 op het scherm = `10:00:00Z`; achterstanden `+ 46` en `+ 01:14` |
| `cyclingflash_uitslag_cx_x2o_oudenaarde_men_elite_2026-11-08.html` | https://cyclingflash.com/race/x2o-badkamers-trofee-oudenaarde-2026/result | browser-fetch | ja (Nys, Vanthourenhout, Kuypers) | positie, renner, rating, leeftijd, ploeg, tijd; vlag; JSON met `country.code`, `birthDate`, tijd in ms, `teamEdition` | `+ 1 Lap`, `+ 3 Laps`, `DNF`; `22 km` tegenover `distance: 22.48`; geen ronden of GPX |
| `cyclingflash_uitslag_cx_x2o_oudenaarde_women_elite_2026-11-08.html` | https://cyclingflash.com/race/x2o-badkamers-trofee-oudenaarde-we-2026/result | browser-fetch | ja (Brand, Casasola, Schreiber) | idem | `17 km`; slug vorig jaar `...-koppenbergcross-we-2025` |
| `cyclingflash_event_cx_superprestige_niel_2026-11-08.html` | https://cyclingflash.com/event/jaarmarktcross-niel-2026 | browser-fetch | ja (Niel, Superprestige) | per categorie tijdvak start – einde, links | **fout:** Men Juniors `12:00 - 11:40`; geen U23 |
| `cyclingflash_startlijst_cx_superprestige_niel_men_elite_2026-11-08.html` | https://cyclingflash.com/race/telenet-superprestige-niel-2026/startlist | browser-fetch | ja (Niel); Nys/Vanthourenhout staan er nog niet op | rugnummer (leeg), renner, ploeg; infoblok met `Times 15:10 - 16:10` | pas 3 renners; losse tekst `Cyclocross418` |
| `cyclingflash_stand_cx_superprestige_men_elite_2026-11-08.html` | https://cyclingflash.com/serie/telenet-superprestige-2026-2027-men-elite | browser-fetch | ja (Overijse, Middelkerke, Wyseure) | manches met datum en winnaar; stand: positie, verschuiving, renner, punten; peildatum | datum plakt aan naam, formaat `DD-MM-JJJJ` |
| `cyclingflash_tvgids_2026-11-08.html` | https://cyclingflash.com/tv-guide | browser-fetch | ja (Niel, Sporza, Eurosport) | per koers: klasse, categorie; per uitzending: tijdvak, zender (aanbieder), landen; JSON met UTC en verwachte start/finish | tijden Europe/Brussels; tekst plakt (`NielC1`, `14:35PlaySports(Telenet)`) |
| `cyclingflash_kalender_weg_2026_men_elite_2026-11-08.html` | https://cyclingflash.com/calendar/road/2026/men-elite | browser-fetch | ja | datum, koers + link, vlag, UCI-klasse, winnaar/startlijst | standaard huidige maand; 12 maandpagina's; seizoenkiezer met 2027 en 2028 |
| `cyclingflash_kalender_weg_2026_women_elite_2026-11-08.html` | https://cyclingflash.com/calendar/road/2026/women-elite | browser-fetch | ja | idem | Alexandria Ladies dubbel (`-we-2026` en `-we-2026-2`) |
| `cyclingflash_kalender_weg_2026_women_elite_augustus_2026-11-08.html` | https://cyclingflash.com/calendar/road/2026/women-elite/8 | browser-fetch | ja (WWT, Pro) | idem; klassen 2.WWT, 1.WWT, 1.Pro, 1.1, 1.2, 2.2, CN, CRTP | Colmar-criterium bij de vrouwen met winnaar Romain Grégoire |
| `cyclingflash_kalender_weg_2027_men_elite_januari_2026-11-08.html` | https://cyclingflash.com/calendar/road/2027/men-elite/1 | browser-fetch | ja (Tour Down Under) | idem | 2027 bestaat al (20 koersen); Mexico-NK dubbel |
| `cyclingflash_overzicht_weg_vuelta_2026-11-08.html` | https://cyclingflash.com/race/vuelta-a-espana-2026 | browser-fetch | ja (Stage 14, General classification) | klasse 2.UWT, etappes, km, data, start/finish, eindstand top 3, truien, ritwinnaars, links per rit naar gc/points/mountain/youth | etappe 3 `Cancelled`; rit 1 zonder `mountain` |
| `cyclingflash_uitslag_weg_vuelta_etappe14_2026-11-08.html` | https://cyclingflash.com/race/vuelta-a-espana-2026/result/stage-14 | browser-fetch | ja (Enric Mas) | ritverloop, tabel positie/renner/rating/leeftijd/ploeg/tijd; JSON met tussensprints en bergen (`kmMarker`, `points`, `bonusSeconds`) | AK staat níet op deze pagina; ±1 MB |
| `cyclingflash_klassement_weg_vuelta_etappe14_gc_2026-11-08.html` | https://cyclingflash.com/race/vuelta-a-espana-2026/result/stage-14/gc | browser-fetch | ja (Enric Mas) | positie, verschuiving (▲/▼), renner, leeftijd, ploeg, tijd | klassement ná etappe 14 (Mas 49:28:12) |
| `cyclingflash_startlijst_weg_vuelta_2026-11-08.html` | https://cyclingflash.com/race/vuelta-a-espana-2026/startlist | browser-fetch | ja (Enric Mas, Movistar) | per ploeg: type, x/8, rugnummers, renners, ploegleiders; tellers renners/in koers/uitvallers | ±2,2 MB; ploegnaam wisselt (`UAE Team Emirates XRG` / `UAE Emirates XRG`) |
| `cyclingflash_uitslag_weg_il_lombardia_2026-11-08.html` | https://cyclingflash.com/race/il-lombardia-2026/result | browser-fetch | ja (Pogačar, DNF) | volledige uitslag, zelfde kolommen; `1.UWT`, `10 Oct · 240 km` | 240 km tegenover 239 km bij TNT |
| `cyclingflash_overzicht_weg_giro_toscana_femminile_2026-11-08.html` | https://cyclingflash.com/race/premondiale-giro-toscana-int-femminile-memorial-michela-fanini-we-2026 | browser-fetch | ja (Swierenga) | zelfde opbouw als het Vuelta-overzicht | 2.2, 27–30 aug; rit 1 alleen gc/youth |
| `cyclingflash_uitslag_weg_giro_toscana_femminile_etappe4_2026-11-08.html` | https://cyclingflash.com/race/premondiale-giro-toscana-int-femminile-memorial-michela-fanini-we-2026/result/stage-4 | browser-fetch | ja (Swierenga, Stage 4) | ritverloop, uitslagtabel | gelijke tijd staat als een losse `"` |
| `tntsports_uitslag_weg_il_lombardia_2026-11-08.html` | https://www.tntsports.co.uk/cycling/il-lombardia/2026/calendar-results.shtml | curl | ja, maar alleen de winnaar (Seixas) | datum, `Road race \| Men`, start → finish / km, winnaar, status, link | namen afgekort (`P. Seixas`); alleen winnaar |
| `tntsports_overzicht_weg_vuelta_2026-11-08.html` | https://www.tntsports.co.uk/cycling/vuelta-a-espana/2026/calendar-results.shtml | curl | ja (ritwinnaars) | per rit: datum, type, start → finish / km, winnaar, status, links | rit 3 `Completed` zonder winnaar; tijdrit heet `Flat` |
| `tntsports_wedstrijd_weg_vuelta_etappe14_2026-11-08.html` | https://www.tntsports.co.uk/cycling/vuelta-a-espana/2026/live-road-race-men-stage-14-jaen-sierra-de-la-pandera_mtc1651434/live-commentary.shtml | curl | ja (liveblog, podium) | podium met IOC-landcode, tabs, liveblog met tijden | tijden in Britse tijd (`GMT+1`) |
| `tntsports_uitslag_weg_vuelta_etappe14_2026-11-08.html` | https://www.tntsports.co.uk/cycling/vuelta-a-espana/2026/live-road-race-men-stage-14-jaen-sierra-de-la-pandera_mtc1651434/live-results.shtml | curl | **deels**: 20 rijen; rest via XHR | positie, renner (afgekort), ploeg, tijd; vlag als afbeelding zonder alt | `hasNextPage: true` |
| `tntsports_klassement_weg_vuelta_etappe14_2026-11-08.html` | https://www.tntsports.co.uk/cycling/vuelta-a-espana/2026/live-road-race-men-stage-14-jaen-sierra-de-la-pandera_mtc1651434/live-table.shtml | curl | ja, 30 rijen | tabs General/Team/Points/Mountain/Youth/Combativity; positie, renner, ploeg, tijd | **toont het eindklassement**, niet de stand na rit 14; `MOVISTAR`, slug `lotto-nl-jumbo` |
| `tntsports_kalender_cx_2026-11-08.html` | https://www.tntsports.co.uk/cyclo-cross/score-center.shtml | curl | **nee**: geen enkele cross | dagkiezer 1–15 nov, `No match available` | leeg op de dag van het EK |
| `tntsports_uitslag_weg_vuelta_etappe14_graphql_2026-11-08.json` | `https://netsport.eurosport.io/?…operationName=inArenaTableByIdQuery…` (volledig in README) | XHR-adres, opgehaald met curl + header `domain: www.tntsports.co.uk` | nvt (JSON) | per rij positie, naam + korte naam, land (naam + code), ploeg (naam + code), tijd | rijen 21–70; persisted query (sha256-hash) |
| `aso_racecenter_etappes_tdf_2026_2026-11-08.json` | `https://racecenter.letour.fr/api/stage-2026?xdt=…` | XHR-respons uit de browsercache | nvt (JSON) | etappe, datum, `startTime`, `endTime`, `timezone`, lengte, type, `isCancelled`, start-/finishplaats | niet gesorteerd; `xdt`-token in elk adres |
| `aso_racecenter_klassement_tdf_2026_etappe21_2026-11-08.json` | `https://racecenter.letour.fr/api/rankingType-2026-21?xdt=…` | XHR-respons uit de browsercache | nvt (JSON) | per klassement: type, checkpoint, rugnummer, positie, tijd (ms), bonus, `penality`, `$rider`-verwijzing | geen namen (staan in `allCompetitors-2026`); 191 checkpointrecords ertussen |
| `superprestige_manche_cx_niel_2026-11-08.html` **(r2)** | https://www.superprestigecyclocross.be/nl/kalender/2026-2027/niel | curl | ja | datum, adres, parkings, tv per land, **programma met starttijd per categorie** | juniorentijden andersom dan bij CyclingFlash |
| `superprestige_uitslagen_cx_2026-11-08.html` **(r2)** | https://www.superprestigecyclocross.be/nl/uitslagen | curl | ja | per manche en categorie top 3 met land (IOC) en tijd; PDF-link | volledige uitslag alleen als PDF |
| `superprestige_uitslag_cx_overijse_men_elite_2026-11-08.pdf` **(r2)** | https://www.superprestigecyclocross.be/nl/files/5ab96bc7-d089-11f1-bd5d-0050569301fd/1792942377 | curl | nvt (PDF) | plaats, **rugnummer**, naam, UCI-code, **UCI-id**, categorie, ploeg, tijd, achterstand; **afstand 27,9 km**, gem. snelheid, deelnemers | ploegnamen afgekapt; `´` als minutenteken |
| `x2otrofee_kalender_en_klassement_cx_2026-11-08.html` **(r2)** | https://x2otrofee.be/ | curl | ja | kalender (datum met jaar, cross, plaats, organisatorsite); tijdsklassement top 3 | klassementstijd ≠ koerstijd |
| `x2otrofee_uitslagen_cx_2026-11-08.html` **(r2)** | https://x2otrofee.be/uitslagen/ | curl | ja (alleen links) | per manche link naar uitslag op de organisatorsite | vorige-seizoensmanche in de lijst |
| `ucicxworldcup_kalender_cx_2026-11-08.html` **(r2)** | https://www.ucicyclocrossworldcup.com/en/calendar | curl | ja | datum `DD/MM/JJ`, plaats, link per manche | slugs als `namur-7` |
| `ucicxworldcup_manche_cx_ostrava_2026-11-08.html` **(r2)** | https://www.ucicyclocrossworldcup.com/en/calendar/2026-2027/ostrava | curl | ja | programma met tijden (Women Elite 18:15, Men Elite 19:45) | aparte dag voor junioren |
| `veloracycling_koers_cx_superprestige_merksplas_2026-11-08.html` **(r2)** | https://veloracycling.com/races/aarbeiencross-2026 | curl | ja | datum, klasse, starttijd per categorie ("local time"), serietabel; JSON-LD `SportsEvent` | typefout `Aarbeiencross` |
| `veloracycling_kalender_2026-11-08.html` **(r2)** | https://veloracycling.com/races | curl | ja | maand, koers, type, links naar uitslagartikelen | **toont seizoen 2025** |
| `domestiquecycling_kalender_weg_2026_2026-11-08.html` **(r2)** | https://www.domestiquecycling.com/en/cycling-races/2026/ (→ `/en/cycling-races/`) | curl | ja | datum met jaar, koers, **geslacht**, UCI-klasse, winnaar/leider | geen cross; *Upcoming* ongesorteerd |
| `domestiquecycling_koers_weg_il_lombardia_2026-11-08.html` **(r2)** | https://www.domestiquecycling.com/en/cycling-races/il-lombardia/2026/ | curl | ja | route, km, hoogtemeters, datum, geslacht, klasse, land | — |
| `domestiquecycling_uitslag_weg_il_lombardia_2026-11-08.html` **(r2)** | https://www.domestiquecycling.com/en/cycling-races/il-lombardia/2026/race-results/ | curl | ja | positie, renner, ploeg, tijd | achterstand `+ 00.48` (punt) |
| `eurosportnl_kalender_cx_2026-11-08.html` **(r2)** | https://www.eurosport.nl/veldrijden/score-center.shtml | curl | **nee** | dagkiezer, `Geen uitslagen beschikbaar` | zelfde lege pagina als TNT |
| `uci_kalender_2026-11-08.html` **(r2)** | https://www.uci.org/calendar/all/2jnxYAuvjgttyHi6YQ94EJ | curl | **nee** (JavaScript) | alleen app-skelet | data via de JSON hieronder |
| `uci_kalender_upcoming_2026-11-08.json` **(r2)** | https://www.uci.org/api/calendar/upcoming | XHR-adres (gezien in browser), opgehaald met curl | nvt (JSON) | naam, discipline, plaats, land, werelddeel, datumtekst, detaillink | 3.616 vermeldingen t/m april 2028; geen klasse, geen geslacht |
| `uci_wedstrijd_cx_superprestige_niel_2026-11-08.html` **(r2)** | https://www.uci.org/competition-details/2027/CRO/79146 | curl | ja | klasse C1, races per categorie, jury | geen tijden, geen uitslag |
| `wikipedia_superprestige_cx_2026_2027_2026-11-08.html` **(r2)** | https://en.wikipedia.org/wiki/2026%E2%80%9327_Cyclo-cross_Superprestige | curl | ja | kalender met ISO-datum en klasse; podium per manche met land; stand | **Overijse fout (26 okt)**; loopt achter |
| `cyclingstage_kalender_2027_2026-11-08.html` **(r3)** | https://www.cyclingstage.com/uci/cycling-calendar-2027/ | curl | ja | dagen, koers, land; route/uitslag leeg | het eigen `KALENDER_URL` van de integratie bestaat al voor 2027 |
| `cyclingstage_wk_2026_route_wegrit_vrouwen_2026-11-08.html` **(r3)** | https://www.cyclingstage.com/world-championships-2026-montreal/route-road-race-wc-2026-women/ | curl | ja | afstand, hoogtemeters, ronde, **eigen GPX** `route-women.gpx` | beantwoordt `gevraagde-paginas.md` |
| `cyclingstage_vuelta_2026_puntenklassement_2026-11-08.html` **(r3)** | https://www.cyclingstage.com/vuelta-2026-points-classification/ | curl | ja | top 5 + leider per etappe | `Gruisan` (typefout) |
| `cyclingstage_vuelta_2026_bergklassement_2026-11-08.html` **(r3)** | https://www.cyclingstage.com/vuelta-2026-kom-classification/ | curl | ja | top 5 + leider per etappe | — |
| `cyclingstage_vuelta_2026_uitvallers_2026-11-08.html` **(r3)** | https://www.cyclingstage.com/vuelta-2026/vuelta-2026-withdrawals/ | curl | ja | DNF/DNS per etappe, rugnummer, naam, land, ploeg | eigen landcodes; "23 August" fout |
| `cyclingstage_tour_of_britain_2026_koers_2026-11-08.html` **(r3)** | https://www.cyclingstage.com/tour-of-britain-2026/ | curl | ja | alleen links naar renners, route, winnaars | geen etappe- of uitslagpagina |
| `cyclingstage_ronde_van_vlaanderen_vrouwen_2026_2026-11-08.html` **(r3)** | https://www.cyclingstage.com/tour-of-flanders-2026-women/ | curl | ja | samenvatting, links route/riders/results | — |
| `cyclingstage_ronde_van_vlaanderen_vrouwen_2026_route_2026-11-08.html` **(r3)** | https://www.cyclingstage.com/tour-of-flanders-2026-women/route-women-tof-2026/ | curl | ja | route als tekst, GPX `route-women.gpx` | geen starttijd |
| `cyclingstage_giro_2026_route_2026-11-08.html` **(r3)** | https://www.cyclingstage.com/giro-2026-route/italy-route-2026/ | curl | ja | totalen, data, etappelinks `stage-N-italy-2026` | — |
| `cyclingstage_giro_2026_etappe14_2026-11-08.html` **(r3)** | https://www.cyclingstage.com/giro-2026-route/stage-14-italy-2026/ | curl | ja | tekst, cols, GPX, profielplaatjes, **link "timings" naar `stage-14-times.jpg`** | "tussensprint km 116" is de Red Bull-km |
| `cyclingstage_giro_2026_etappe14_tijdschema_2026-11-08.jpg` **(r3)** | https://www.cyclingstage.com/images/giro-italy/2026/stage-14-times.jpg | curl | nvt (afbeelding) | RCS-cronotabella: hoogte, plaats, km, passeertijden bij 3 snelheden, sprint, cols | alleen met OCR leesbaar |
| `cyclingflash_etappe_weg_vuelta_etappe14_2026-11-08.html` **(r3)** | https://cyclingflash.com/race/vuelta-a-espana-2026/stages/stage-14 | browser-fetch | ja | km, hoogtemeters, aantal klimmen, slotkm-%, profieltype, start/finish (UTC), **SVG-mini-profiel**, winkans | 154,5 tegenover 152,7 km |
| `domestiquecycling_profiel_weg_il_lombardia_2026-11-08.html` **(r3)** | https://www.domestiquecycling.com/en/cycling-races/il-lombardia/2026/race-profile/ | curl | ja | alleen tekst | **geen profiel** ondanks de naam |
| `aso_racecenter_hoogteprofiel_tdf_2026_etappe21_2026-11-08.csv` **(r3)** | https://racecenter.letour.fr/profils/2026/profile-21-tiny-c039761a4e729cd2c42426cebe111b52.csv | XHR-respons uit de browsercache | nvt (CSV) | per 100 m: coördinaten, hoogte, helling, km, hoogtemeters, checkpointtype, **colcategorie** | geen token; hash-herkomst onbekend |
| `aso_racecenter_tijdschema_tdf_2026_etappe21_2026-11-08.json` **(r3)** | `https://racecenter.letour.fr/api/checkpointList-2026-21?xdt=…` | XHR-respons uit de browsercache | nvt (JSON) | per checkpoint: plaats, km, passeertijden (3 snelheden), sprint, karavaan, **weer** | officieel tijdschema |

### 3. Antwoorden cross

Wielerflits en Sporza zijn niet bekeken (robots.txt, zie §1). De antwoorden gaan dus alleen over CyclingFlash en TNT Sports.

**Welke bron heeft een gestructureerde kalender (datum, plaats, serie, geslacht)?**
- Antwoord: **CyclingFlash.** Per rij datum (`DD.MM`, zonder jaar), koersnaam, landvlag, klasse en winnaar of startlijstlink. Het geslacht zit in de URL (`/men-elite/`, `/women-elite/`). Serie en plaats zitten alleen in de koersnaam (`Telenet Superprestige - Niel`), niet in een eigen kolom. De seriepagina geeft per serie alle manches met datum. TNT Sports: nee, de crosspagina is leeg.
- Bron: CyclingFlash.
- Bewijs: `cyclingflash_kalender_cx_men_elite_2026-11-08.html`, `cyclingflash_kalender_cx_women_elite_2026-11-08.html`, `cyclingflash_stand_cx_superprestige_men_elite_2026-11-08.html`, `tntsports_kalender_cx_2026-11-08.html`.

**Welke heeft een uitslag (positie, naam, land/ploeg, tijd/achterstand)?**
- Antwoord: **CyclingFlash**, volledig: positie, naam, leeftijd, ploeg, tijd of achterstand, `+ N Laps` en `DNF`. Het land staat als vlagafbeelding in de HTML en als `country.code` in de ingebedde JSON. De eventpagina geeft per categorie de top 3.
- Bron: CyclingFlash.
- Bewijs: `cyclingflash_uitslag_cx_x2o_oudenaarde_men_elite_2026-11-08.html`, `cyclingflash_uitslag_cx_x2o_oudenaarde_women_elite_2026-11-08.html`, `cyclingflash_event_cx_x2o_oudenaarde_2026-11-08.html`.

**Welke heeft starttijden per categorie?**
- Antwoord: **CyclingFlash.** Verreden cross: starttijd per categorie op de eventpagina (Oudenaarde 11:00 / 11:00 / 12:10 / 13:45 / 15:00), in de JSON als UTC (`"start":"2026-11-01T10:00:00Z"`). Komende cross: tijdvak start – einde (Niel: `15:10 - 16:10` voor Men Elite), ook in het infoblok van de startlijst. Let op de datafout `12:00 - 11:40` bij Men Juniors in Niel. De tv-gids geeft per uitzending ook de verwachte start (`stage.start`) en finish (`finishExpectedFast`).
- Bron: CyclingFlash.
- Bewijs: `cyclingflash_event_cx_x2o_oudenaarde_2026-11-08.html`, `cyclingflash_event_cx_superprestige_niel_2026-11-08.html`, `cyclingflash_startlijst_cx_superprestige_niel_men_elite_2026-11-08.html`, `cyclingflash_tvgids_2026-11-08.html`.

**Is er ergens een parcourskaart/GPX of een rondeafstand en aantal ronden?**
- Antwoord: **Nee.** Alleen de totale afstand (`22 km` / `"distance":22.48` bij de mannen, `17 km` bij de vrouwen). Geen rondeafstand, geen aantal ronden, geen GPX en geen kaart gevonden. Gedubbelde renners staan als `+ N Laps`.
- Bron: CyclingFlash (gezocht op `gpx`, `lapDistance`, `circuit`, `course`).
- Bewijs: `cyclingflash_uitslag_cx_x2o_oudenaarde_men_elite_2026-11-08.html`.

**Aanvulling uit ronde 2 (op de vier vragen):**
- *Kalender*: de **officiële seriesites** (Superprestige, X²O, wereldbeker) hebben elk een kalender met datum en plaats; X²O met jaar en weekdag. De serie zit daar impliciet in de site. **UCI** (`uci_kalender_upcoming_2026-11-08.json`) heeft alle crossen wereldwijd met datum, plaats en land, maar zonder klasse en geslacht. Klasse en categorieën staan op de UCI-detailpagina (`uci_wedstrijd_cx_superprestige_niel_2026-11-08.html`). **Wikipedia** heeft een kalender met ISO-datum en klasse, maar met een fout (Overijse 26 in plaats van 25 oktober).
- *Uitslag*: de **Superprestige-PDF** is de officiële volledige uitslag, met rugnummer, UCI-id, land (in de UCI-code), ploeg, tijd en achterstand (`superprestige_uitslag_cx_overijse_men_elite_2026-11-08.pdf`). De Superprestige-uitslagenpagina en Wikipedia geven alleen het podium met land. X²O verwijst voor uitslagen naar de sites van de organisatoren.
- *Starttijden per categorie*: **officiële Superprestige-pagina per manche** (Niel: Junioren Mannen 10:30, Junioren Vrouwen 12:00, Elite Vrouwen 13:40, Elite Mannen 15:10), **wereldbekerpagina per manche** (Ostrava: Women Elite 18:15, Men Elite 19:45) en **Velora** (Merksplas: Elite Women 13:40, Elite Men 15:10, "local time"). Let op: CyclingFlash heeft de juniorentijden van Niel omgedraaid ten opzichte van de officiële site.
- *Parcours*: nog steeds geen GPX, rondeafstand of aantal ronden. Wel staan **totale afstand (27,9 km) en gemiddelde snelheid** in de Superprestige-PDF.

Extra, bij B1/B2 (tv-gids voor cross): ook de officiële Superprestige-manchepagina noemt de zenders per land (`BEL - Play Sports & Pickx+ Sports`, `NLD - Eurosport 1` …), zonder tijden. CyclingFlash heeft een tv-gids met per cross de zenders (Sporza/VRT1, NPO1, PlaySports, Eurosport, HBO Max, TNT Sports, RTBF, Proximus) en tijden. Bewijs: `cyclingflash_tvgids_2026-11-08.html`. De gevraagde Wielerflits-tv-gidsen zijn niet opgehaald.

### 4. Antwoorden weg

**C1. Wegkalender 2026 (Men Elite en Women Elite), aantal pagina's, UCI-klasse, links, 2027?**
- Antwoord: Wielerflits niet opgehaald (robots). Op **CyclingFlash** is de kalender per maand opgedeeld: 12 pagina's (`/calendar/road/2026/{men-elite|women-elite}/{1..12}`); het adres zonder maand toont de huidige maand. De **UCI-klasse staat erbij** als code (`2.UWT`, `1.UWT`, `2.WWT`, `1.WWT`, `1.Pro` = ProSeries, `1.1`, `2.1`, `2.2`, `1.2`, `CN`, `CRTP`). Per koers is er een link naar `/race/{slug}` (met tabs Info/Startlist/Stages/Results/Winners) en een winnaar- of startlijstlink. **De kalender van 2027 bestaat al**: januari 2027 heeft 20 koersen, en de seizoenkiezer kent ook 2028.
- Bron: CyclingFlash.
- Bewijs: `cyclingflash_kalender_weg_2026_men_elite_2026-11-08.html`, `cyclingflash_kalender_weg_2026_women_elite_2026-11-08.html`, `cyclingflash_kalender_weg_2026_women_elite_augustus_2026-11-08.html`, `cyclingflash_kalender_weg_2027_men_elite_januari_2026-11-08.html`.

**C2. Vuelta 2026: etappeoverzicht, etappe-uitslag met AK, startlijst; punten-, berg- en jongerenklassement?**
- Antwoord: Op **CyclingFlash** alle drie aanwezig. Het AK staat níet op de ritpagina zelf maar op een eigen URL (`/result/stage-14/gc`); die is ook opgeslagen. **Punten-, berg- en jongerenklassement bestaan** als aparte URL's per rit (`/points`, `/mountain`, `/youth`). De links heb ik gezien, de pagina's heb ik niet opgehaald. De startlijst heeft rugnummers en uitvallers.
- Bron: CyclingFlash.
- Bewijs: `cyclingflash_overzicht_weg_vuelta_2026-11-08.html`, `cyclingflash_uitslag_weg_vuelta_etappe14_2026-11-08.html`, `cyclingflash_klassement_weg_vuelta_etappe14_gc_2026-11-08.html`, `cyclingflash_startlijst_weg_vuelta_2026-11-08.html`.

**C3. Il Lombardia 2026, uitslag?**
- Antwoord: **CyclingFlash** heeft de volledige uitslag (incl. DNF). **TNT Sports** toont op de kalenderpagina alleen de winnaar (`P. Seixas`, 5:49:28 in de ingebedde JSON).
- Bron: CyclingFlash, TNT Sports.
- Bewijs: `cyclingflash_uitslag_weg_il_lombardia_2026-11-08.html`, `tntsports_uitslag_weg_il_lombardia_2026-11-08.html`.

**C4. Een vrouwenronde die cyclingstage niet heeft?**
- Antwoord: Simac Ladies Tour en Tour de Romandie Féminin stonden niet op de opgehaalde augustuspagina; verder heb ik niet gezocht. In plaats daarvan: de **Premondiale Giro Toscana Int. Femminile** (2.2, 27–30 aug). Overzicht en etappe 4 opgeslagen, met dezelfde structuur als de Vuelta. **Of cyclingstage deze koers mist, heb ik niet gecontroleerd.**
- Bron: CyclingFlash.
- Bewijs: `cyclingflash_overzicht_weg_giro_toscana_femminile_2026-11-08.html`, `cyclingflash_uitslag_weg_giro_toscana_femminile_etappe4_2026-11-08.html`.

**C5. TNT Sports: volledige uitslag, klassement, startlijst, of alleen de winnaar?**
- Antwoord: De pagina's `calendar-results.shtml` geven **alleen de winnaar** (per eendagskoers of per rit). Per rit is er een wedstrijdpagina met tabbladen. **Results**: de eerste 20 rijen in de HTML, daarna per 50 via GraphQL (`netsport.eurosport.io`, `inArenaTableByIdQuery`). **Overall standings**: bij etappe 14 staat het **eindklassement**, niet de stand na die rit. Een **startlijst** heb ik nergens gezien. Namen zijn afgekort (`M. Brenner`).
- Bron: TNT Sports.
- Bewijs: `tntsports_overzicht_weg_vuelta_2026-11-08.html`, `tntsports_uitslag_weg_vuelta_etappe14_2026-11-08.html`, `tntsports_uitslag_weg_vuelta_etappe14_graphql_2026-11-08.json`, `tntsports_klassement_weg_vuelta_etappe14_2026-11-08.html`, `tntsports_wedstrijd_weg_vuelta_etappe14_2026-11-08.html`.

**C6. CyclingFlash: openbare kalender- of uitslagpagina?**
- Antwoord: **Ja**, beide, plus startlijsten, series, tv-gids en per rit klassementen. Kanttekening: **curl kreeg HTTP 403 met een Cloudflare-uitdaging** (`cf-mitigated: challenge`). Alleen in een echte browser kwam de pagina door.
- Bron: CyclingFlash.
- Bewijs: alle `cyclingflash_*`-bestanden. Het 403-antwoord is niet als fixture opgeslagen.

**Aanvulling uit ronde 2 (weg):**
- *C1, kalender*: **Domestique Cycling** zet het hele jaar 2026 op één pagina, met datum **inclusief jaar**, **geslacht als eigen kolom**, UCI-klasse (ook `1.Pro`/`2.Pro`) en winnaar. Kanttekeningen: geen cross, en de *Upcoming*-lijst is niet gesorteerd. **UCI** levert via `api/calendar/upcoming` een JSON-kalender t/m april 2028 (Lombardia 2027 staat er al in), maar zonder klasse en geslacht. Bewijs: `domestiquecycling_kalender_weg_2026_2026-11-08.html`, `uci_kalender_upcoming_2026-11-08.json`.
- *C3, Lombardia*: **Domestique** heeft de volledige uitslag (positie, renner, ploeg, tijd) en een koerspagina met afstand, hoogtemeters, geslacht en klasse. Achterstanden staan met een punt (`+ 00.48`). Bewijs: `domestiquecycling_uitslag_weg_il_lombardia_2026-11-08.html`, `domestiquecycling_koers_weg_il_lombardia_2026-11-08.html`.
- *C2/C4/C5*: in ronde 2 niet verder onderzocht. Domestique heeft per koers ook een startlijsttab (link gezien, niet opgehaald).
- *Afgevallen*: ProCyclingStats en FirstCycling (robots.txt), Velora (kalender toont nog 2025).

**Aanvulling uit ronde 3 (normale koersdata en hoogteprofiel):**
- *Hoogteprofiel*: naast de cyclingstage-GPX zijn er twee echte alternatieven. **ASO-profiel-CSV**: één punt per 100 m met hoogte, helling en officiële colcategorie, alleen voor ASO-koersen. **CyclingFlash**: een genormaliseerd SVG-mini-profiel plus hoogtemeters, aantal klimmen en slotkilometer-%; geen meters. Domestique, TNT, UCI en Velora hebben geen profieldata. Bewijs: `aso_racecenter_hoogteprofiel_tdf_2026_etappe21_2026-11-08.csv`, `cyclingflash_etappe_weg_vuelta_etappe14_2026-11-08.html`, `domestiquecycling_profiel_weg_il_lombardia_2026-11-08.html`.
- *Tijdschema en tussensprint*: cyclingstage heeft het tijdschema als **JPG** (`stage-N-times.jpg`, gelinkt vanaf de etappepagina), niet als `.htm`. ASO heeft het als JSON (`checkpointList`). Bewijs: `cyclingstage_giro_2026_etappe14_tijdschema_2026-11-08.jpg`, `aso_racecenter_tijdschema_tdf_2026_etappe21_2026-11-08.json`.
- *Klassementen en uitvallers*: cyclingstage geeft nu top 5 plus leider per etappe, en uitvallers per etappe. Bewijs: de drie `cyclingstage_vuelta_2026_*`-bestanden.
- *Kalender 2027*: bestaat al bij cyclingstage op het adres dat de integratie zelf gebruikt. Bewijs: `cyclingstage_kalender_2027_2026-11-08.html`.

**C7. ASO racecenter: JSON-adressen?**
- Antwoord: De racecenter (nu op Tour 2026, etappe 21) laadt onder andere `https://racecenter.letour.fr/api/` + `event`, `stage-2026`, `team-2026`, `allCompetitors-2026`, `rankingType-2026-20`, `rankingType-2026-21`, `rankingTypeJerseys-2026-21`, `rankingTypeJerseys-2026-22`, `rankingTypeArrival-2026-21`, `checkpointList-2026-21`, `checkpoint-2026-21`, `pack-2026-21`, `telemetryCompetitor-2026`, `telemetryPack-2026-21`, `flashInfoLive-2026-21`, `insights-2026-21`, `publication_en-2026-21`, `extraVehicle-2026-21`, `social`, `ad`, plus het profiel `https://racecenter.letour.fr/profils/2026/profile-21-tiny-….csv`. **Elk API-adres draagt een `?xdt=…`-token.** Opgeslagen: de etappelijst (met start- en eindtijd en tijdzone) en het klassement na etappe 21 (zonder namen; die staan in `allCompetitors-2026`).
- Bron: ASO racecenter.
- Bewijs: `aso_racecenter_etappes_tdf_2026_2026-11-08.json`, `aso_racecenter_klassement_tdf_2026_etappe21_2026-11-08.json`.

### 5. Niet gelukt

| adres | wat er gebeurde | wat ik geprobeerd heb |
|---|---|---|
| https://www.wielerflits.nl/nieuws/veldrijden-op-tv/ | Niet opgehaald: robots.txt `User-Agent: ClaudeBot` / `Disallow: /` | Niets (regel 3) |
| https://www.wielerflits.nl/nieuws/wielrennen-op-tv/ | idem | Niets |
| https://wielerflits.be/wielerkalender/road/2025/Men%20Elite/1 en het cross-equivalent (Men/Women Elite 2026-2027) | idem (wielerflits.be → www.wielerflits.be, zelfde regel) | Niets |
| Wielerflits: uitslag en startlijst Superprestige Overijse / X²O Oudenaarde, Niel, seriestand | idem | Niets. Vervangen door CyclingFlash. |
| https://wielerflits.be/wielerkalender/road/2026/Men%20Elite/1 en `Women%20Elite` | idem | Niets |
| Wielerflits: Vuelta 2026, Il Lombardia 2026, Simac/Romandie Féminin | idem | Niets. Vervangen door CyclingFlash. |
| https://sporza.be/nl/2026/09/29/wanneer-is-welke-cross-en-welke-wedstrijden-zijn-live-bij-sporza-dit-is-de-complete-veldritkalender-2026-2027~1790685673220/ | Niet opgehaald: robots.txt `User-agent: ClaudeBot` / `Disallow: /` | Niets |
| https://sporza.be/nl/categorie/wielrennen/veldrijden/superprestige-veldrijden/ | idem | Niets |
| Sporza: uitslagartikel van een verreden cross | idem | Niets |
| https://cyclingflash.com/ (met curl) | **HTTP 403**, `cf-mitigated: challenge`, `server: cloudflare` (Cloudflare-uitdaging) | Uitdaging niet omzeild. In de ingebouwde browser geopend, waar de check vanzelf slaagde; alle CyclingFlash-pagina's daarna via `fetch()` in die browser. |
| https://racecenter.letour.fr/robots.txt | Bestaat niet: 302 → `/en/not-found` | Gemeld in §1. De HTML-respons is niet als robots.txt opgeslagen. |
| https://netsport.eurosport.io/robots.txt | Bestaat niet: HTTP 400 JSON-fout | Gemeld in §1 |
| https://www.tntsports.co.uk/cyclo-cross/score-center.shtml | Geen crossdata in de HTML (`No match available`) | Opgeslagen zoals hij is; niet verder onderzocht of andere dagen via JavaScript laden |
| TNT GraphQL na rij 70, Vuelta-punten/berg/jongeren op CyclingFlash, `allCompetitors-2026` op racecenter | Bewust niet opgehaald (geen verdere paginering, hoogstens twee ASO-bestanden) | — |
| https://cyclocross24.com/ **(ronde 2)** | Niet opgehaald: robots.txt `User-agent: ClaudeBot` / `Disallow: /` | Niets |
| https://www.procyclingstats.com/ en https://cx.procyclingstats.com/ **(ronde 2)** | Niet opgehaald: `ClaudeBot` en `Claude-User` → `Disallow: /` | Niets |
| https://firstcycling.com/ **(ronde 2)** | Niet opgehaald: `User-agent: *` en `ClaudeBot` → `Disallow: /` | Niets |
| X²O-uitslagen (bijv. https://koppenbergcross.be/uitslagen-en-erelijst/) **(ronde 2)** | Niet opgehaald: ligt op de site van elke organisator apart; robots.txt van die hosts niet gelezen | Alleen de link genoteerd |
| Tissot Timing / officiële live timing van de wereldbeker **(ronde 2)** | Niet gevonden: de webzoektocht leverde geen adres op | Twee zoekopdrachten; niets opgehaald |
| https://www.cyclingstage.com/tour-of-britain-2026/stage-4-gb-2026/ en https://www.cyclingstage.com/tour-of-britain-2026-results/ **(r3)** | **HTTP 404** (beide adressen komen uit `docs/gevraagde-paginas.md`) | Koerspagina en routepagina doorzocht op links naar etappes of uitslagen: geen gevonden. De 404-pagina's zijn niet als fixture bewaard. |
| https://secure.tourtrackerdata.com/ **(r3)** | Niet opgehaald: `User-agent: *` / `Disallow: /` | Alleen robots.txt gelezen |
| UCI DataRide **(ronde 2)** | Niet opgehaald: volgens de gevonden UCI-handleiding een inlogplatform voor organisatoren en bonden, geen openbare uitslagensite | Alleen gezocht |

### 6. Onzeker

- **Of de Home Assistant-integratie CyclingFlash kan bereiken.** curl met mijn user-agent kreeg een Cloudflare-uitdaging (403). Vermoeden: aiohttp krijgt hetzelfde. Niet getest, want ik heb geen andere user-agents geprobeerd om de check te omzeilen.
- **CyclingFlash en WielerFlits lijken hetzelfde platform.** De robots.txt-bestanden zijn bijna gelijk van opbouw (`/api/bff/`, `/oidc/`, kalenderfilters `?country=`/`?classification=`) en de CyclingFlash-footer linkt naar TikTok `@wielerflits`. Vermoeden: de Wielerflits-pagina's hebben dezelfde structuur als de opgeslagen CyclingFlash-pagina's. Niet gecontroleerd.
- Dat het kalenderadres zonder maand altijd de **huidige maand** toont: afgeleid van één waarneming (november).
- De teller `44Races` is voor mannen en vrouwen gelijk. Vermoeden: hij telt evenementen.
- De querynamen `?classification=` en `?country=` voor de kalenderfilters heb ik uit robots.txt afgeleid, niet uit de pagina.
- De betekenis van de ASO-codes (`PLN`, `VAL`, `HMG`, `EQU`, `PAS`; `ite`, `itg`, `ipg`, `img`, `ijg`, `etg`, `icg`, `iqg` …) is een vermoeden.
- Of het `xdt`-token van racecenter verplicht is of per verzoek verandert: niet getest (ik heb er bewust geen eigen verzoeken mee gedaan).
- De waarde `www.tntsports.co.uk` voor de `domain`-header heb ik zelf gekozen. De server accepteerde hem, maar wat de site zelf stuurt heb ik niet gezien.
- Dat het TNT-tabblad *Overall standings* altijd de actuele of eindstand toont: één waarneming (etappe 14).
- Tijden in het TNT-liveblog lijken Britse tijd (`GMT+1` op 5 september = BST).
- Of de Giro Toscana Femminile bij cyclingstage ontbreekt: niet gecontroleerd.
- `Grand Prix Navoi Ladies` in augustus `Cancelled` en in november opnieuw (slug `-2`): vermoedelijk verplaatst. Dubbel `National Road Championships - Mexico` in januari 2027: vermoedelijk wegrit en tijdrit.
- **(r3)** Bij 11 cyclingstage- en Domestique-bestanden van ronde 3 is het ophaaltijdstip in de README de **`Date`-header van de server**, niet de klok van curl. Door een fout in mijn eigen script (`| head -1` brak de pijp af) ontbrak de logregel; de bestanden zelf zijn compleet (curl was al klaar). De adressen in die README's zijn de adressen die ik heb opgevraagd.
- **(r3)** Waar de hash in het adres van de ASO-profiel-CSV vandaan komt, en of er naast `tiny` een fijnere versie is: onbekend.
- **(r3)** Of de ASO-API zonder `xdt`-token antwoordt: niet getest.
- **(r3)** Of CyclingFlash `intermediatePoints` (colcategorie, km) ook vóór een etappe vult: niet onderzocht, alleen na afloop gezien.
- **(ronde 2)** Dat de officiële Superprestige-site gelijk heeft over de juniorentijden in Niel en CyclingFlash niet: aanname, omdat het de organisator is.
- **(ronde 2)** Dat het X²O-klassementsverschil (1:01:16 tegenover 01:01:31) door bonificaties komt: vermoeden.
- **(ronde 2)** De slugs van de wereldbekersite (`namur-7`, `tabor-5`) tellen vermoedelijk de edities.
- **(ronde 2)** Of de UCI-API stabiel en bedoeld is voor extern gebruik: onbekend (geen documentatie gevonden).
- **(ronde 2)** Of Velora zijn kalender later naar 2026 bijwerkt, of de pagina is blijven hangen: onbekend.
- De `Final classifications` op de Vuelta-overzichtspagina tonen alleen namen. Welk klassement bij welke naam hoort, staat vermoedelijk alleen in een icoon.

### 7. Advies

1. **Cross: CyclingFlash als hoofdbron** (kalender, volledige uitslagen, starttijden in UTC, standen, tv-gids), **aangevuld met de officiële seriesites** (Superprestige, wereldbeker) voor de starttijden. Die zijn met curl bereikbaar, staan in de ruwe HTML, en Niel laat zien dat CyclingFlash zich kan vergissen.
2. **Weg: CyclingFlash, met Domestique Cycling als terugvaloptie** voor kalender en uitslag. Domestique is met curl bereikbaar, heeft het jaar en het geslacht als eigen velden, maar heeft geen cross. TNT geeft alleen winnaars.
3. **Grote kanttekening:** CyclingFlash gaf curl een Cloudflare-uitdaging (403). Test eerst vanuit Home Assistant of aiohttp erdoor komt. Zo niet, dan zijn de seriesites en Domestique (plus UCI-JSON voor datums) de bruikbare alternatieven.
4. Lees bij CyclingFlash de ingebedde JSON (`self.__next_f.push`), niet de HTML-tabellen: de zichtbare tekst plakt aan elkaar (`NielC1`, `44Races`, `"`).
5. Hoogteprofiel en tijdschema: de cyclingstage-GPX blijft de basis. Voor ASO-koersen levert de racecenter wél officiële colcategorieën en het tijdschema (CSV/JSON; token en hash nog uitzoeken). Lage prioriteit: de UCI-JSON (geen klasse of geslacht), Wikipedia (fout en traag) en Velora (verouderd). ProCyclingStats, FirstCycling en cyclocross24 zijn uitgesloten via robots.txt.
