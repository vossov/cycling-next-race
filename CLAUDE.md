# CLAUDE.md — Cycling Next Race

Context voor Claude Code. Lees dit vóór je iets wijzigt.

## Wat dit is

Home Assistant custom component die de eerstvolgende WorldTour-wielerkoers op een
dashboard zet: hoogteprofiel, cols, tussensprint, uitslagen, klassementen,
tv-zenders. Zowel mannen- als vrouwen-WorldTour.

- Domein: `cycling_next_race`
- Entiteit: `sensor.cycling_next_race`
- Installatie: HACS (custom repository) of handmatig kopiëren
- Configuratie: config flow; het oude YAML-platform wordt geïmporteerd

## Werkafspraken

- **Alle communicatie en codecommentaar in het Nederlands.**
- **Nooit data verzinnen.** Ontbreekt een bron, laat het veld leeg en laat de
  kaart dat onderdeel weglaten. Geen gereconstrueerde profielen, geen
  watchscore zonder onderbouwing, geen geraden tv-zenders. Dit is een harde
  regel van het project; er is meerdere keren op teruggekomen.
- **Benoem onzekerheid expliciet.** Wat niet getest is, zeg je erbij.
- **Uitbrengen gaat met een versienummer, nooit met een commit-hash.** Zie
  "Uitbrengen" verderop. Dit is een algemene voorkeur van de eigenaar en
  geldt voor al zijn projecten.
- **Een afgeronde wijziging mag meteen live.** Staande toestemming van de
  eigenaar (5 september 2026): naar `main` mergen en `vX.Y.Z` taggen hoort
  bij het werk af maken, daar hoeft niet apart om gevraagd te worden. Een
  wijziging die op een branch blijft staan is niet af — hij draait dan
  nergens. Dat gold namelijk voor `v0.23.0`: gemerged, nooit getagd, en
  daardoor liep de installatie van de eigenaar nog maanden op `v0.22.1`
  zonder dat iemand dat zag. Vraag alleen als de wijziging zelf onzeker is
  (niet getest, een gok in een parser), niet omdat uitbrengen een aparte
  stap zou zijn.
- **Elke wijziging aan de integratie hoogt het versienummer op.** In
  dezelfde commit, in `manifest.json` én `const.py`, en die twee blijven
  gelijk. Niet pas bij het taggen: zonder ophoging meldt Home Assistant nog
  de oude versie en weet je bij een probleem niet wat er draait. Patch bij
  een reparatie, minor bij iets nieuws. Alleen aan README, CLAUDE.md of
  tests gezeten? Dan hoeft het niet — daar merkt een draaiende installatie
  niets van.
- **Het nieuwe versienummer staat vooraan in het commitbericht**, als
  `v0.7.1 — korte omschrijving`. Alleen op commits die het nummer echt
  ophogen; geen prefix betekent dus dat de versie niet is aangeraakt, en dat
  maakt een vergeten ophoging meteen zichtbaar. Merge-commits van GitHub
  krijgen niets — de branchcommit eronder draagt het nummer. Reden: Home
  Assistant meldt een nummer en jij wilt van dat nummer naar de commit; niet
  elke versie krijgt een tag (`v0.6.0` nooit gekregen), en dan is
  `git log --oneline` de enige plek waar het nog staat.
- Degradeer netjes: een mislukte scrape logt op debug-niveau en geeft een lege
  lijst terug, nooit een exception naar boven.

## Architectuur

Het werk zit in `custom_components/cycling_next_race/sensor.py`; daaromheen
staan `const.py` (sleutels en standaardwaarden), `config_flow.py` (toevoegen
en het optiescherm), `__init__.py` (config entry opzetten, herladen, en de
kaart registreren) en `www/cycling-next-race-card.js` (de Lovelace-kaart).

- `CyclingCoordinator(DataUpdateCoordinator)` haalt alles op en krijgt de
  opties uit de config entry mee. `self._opt(sleutel)` leest er één, met de
  waarde uit `OPTION_DEFAULTS` als terugval — ook bij onzin in de opslag.
  Niet elke optie is een getal: `_opt_bool` leest een schakelaar (tekst uit
  de opslag telt mee) en `_opt_koersen` een invoerveld met koersen.
- Verversen standaard elke 30 min, 5 min tijdens een live etappe; beide zijn
  instelbaar. De coordinator zet `self.update_interval` dynamisch op basis
  van `show_state == "LIVE"`.
- Wie een instelling toevoegt raakt vier plekken: `const.py` (`CONF_*`,
  `DEFAULT_*`, `OPTION_DEFAULTS`), het schema in `config_flow.py`,
  `strings.json` plus elke vertaling, en de plek in `sensor.py` die hem
  gebruikt. `tests/test_repo.py` faalt als er één achterblijft.
- Alle netwerk-/parse-werk loopt via `self._job(...)` →
  `async_add_executor_job`, want procyclingstats en urllib zijn blokkerend.
- Caches op de coordinator (per dag of per koers geleegd bij een nieuwe dag):
  `_elev_cache`, `_names_cache`, `_tv_cache`, `_sprints_cache`,
  `_startlist_cache` (de startlijst per koers),
  `_gpxindex_cache` (de GPX-adressen die cyclingstage zelf op een rij zet,
  per koers; alleen gevuld als de vaste adressen falen),
  `_other_cache` (dict
  per etappe van de andere koersen; alleen afgeronde etappes komen erin).
  `_tv_cache` bewaart de tv-gids als HTML — op die pagina staan álle koersen
  van de dag, dus één verzoek bedient de tegel en de pop-up samen.
  `_sprints_cache` is een dict per etappe en geen enkele plek, want de
  koersen in de pop-up vragen hem ook op.
  `_elev_cache` heeft `(etappe, aantal punten)` als sleutel: dezelfde etappe
  wordt als komende dag met 60 punten opgehaald en als getoonde etappe met
  200. Stond alleen de URL in de sleutel, dan kreeg het grote profiel de
  kleine versie terug. `_gpx_beschikbaar` houdt los bij of een etappe een
  profiel heeft, want `_gpx_rang` heeft dat nodig om te kiezen wélke koers
  getoond wordt.

### Welke niveaus meedoen (sinds 0.19)

Cyclingstage kent geen UCI-niveaus, dus `NIVEAUS` in `const.py` is nog maar
twee regels: `"m"` (mannen) en `"v"` (vrouwen). Het geslacht komt uit de
koersnaam én uit het adres, twee onafhankelijke signalen.

`OUDE_NIVEAUS` vertaalt de circuitnummers die in bestaande installaties
opgeslagen staan (`1`/`26` → `m`, `24`/`27` → `v`). Zonder die vertaling zou
een bestaande keuze na de update leeg zijn en stil terugvallen op de
standaard.

**De slug-tabellen zijn weg.** `CYCLINGSTAGE_SLUG`, `CYCLINGSTAGE_STAGERACE`,
`CYCLINGSTAGE_ONEDAY` en `CYCLINGSTAGE_ROUTE` stonden met de hand ingevuld en
kostten ons het profiel van de Vuelta. De kalender geeft het adres van elke
koers, en `slug_van()` haalt daar de slug uit — nagelopen op alle 49 koersen
van 2026: 47 leverden exact op wat er met de hand stond, en de twee andere
waren koersen die die tabellen niet eens hadden. `LEIDERSTRUI` en
`GROTE_RONDES` draaien nu op diezelfde slugs (`vuelta`, `giro`,
`tour-de-france`).

### Hoe het vóór 0.19 was

Een niveau is een `circuit=`-nummer bij procyclingstats. `NIVEAUS` in
`const.py` koppelt nummer → naam, of het een vrouwenkalender is, en of het
nummer geverifieerd is:

| nummer | niveau | geverifieerd |
|---|---|---|
| 1 | WorldTour mannen | ja |
| 24 | WorldTour vrouwen | ja |
| 26 | ProSeries mannen | **nee** |
| 27 | ProSeries vrouwen | **nee** |

De ProSeries-nummers konden van hieruit niet worden nagekeken: de proxy laat
procyclingstats niet door (403 op de CONNECT). Een verkeerd nummer levert
stil een lege kalender op, dus dat wordt zichtbaar gemaakt in plaats van
gegokt: `_fetch_calendar` logt een waarschuwing bij nul koersen (met de
toevoeging dat het nummer niet geverifieerd is) en geeft naast de koersen
een telling per niveau terug, die als `levels_diag` in de attributen komt.
Blijkt een nummer fout, dan is dat één regel in `NIVEAUS`.

Twee instellingen, allebei een keuzelijst over dezelfde tabel:

- `levels` — mag op de tegel én in de pop-up. Standaard `["1", "24"]`, dus
  precies wat de integratie altijd al deed. Leeg gevinkt valt terug op die
  standaard; een sensor zonder koersen helpt niemand.
- `levels_popup` — komt er alleen in de pop-up bij.

**De integratie bepaalt wát er wordt opgehaald, de kaart wat er te zien is.**
Sinds 0.11.0 heeft de kaart een eigen `levels` (zie "Dashboard"), zodat er
bovenaan een dashboard iets anders kan staan dan verderop. Die keuze filtert
alleen wat de sensor al levert — staat een niveau hier uit, dan kan geen
enkele kaart het tonen. Wie zich afvraagt waarom een uitgezet niveau tóch in
beeld komt, kijkt naar deze drie plekken: een leeg gevinkte `levels` valt
terug op de WorldTour, `levels_popup` zet een niveau alsnog in de pop-up, en
staat er van de gekozen niveaus niets te koersen dan pakt de tegel liever een
koers uit de pop-up dan niets (`op_tegel or kandidaten`).

`_niveaus_alles` is de unie en bepaalt wat er wordt opgehaald;
`_mag_op_tegel` kijkt of het `level` van een koers in `_niveaus_tegel` zit.
Een koers zonder `level` (kalender uit een oudere versie, of een test) wordt
niet uitgesloten.

Elke koers uit de kalender draagt `level` en krijgt zijn `women`-vlag uit de
tabel; die staat niet op de kalenderpagina zelf. `self._calendar` bevat dus
alle gekozen niveaus door elkaar — er is geen tweede lijst en `cur_idx`
hoort gewoon bij `self._calendar`.

Staat er een niveau alleen in de pop-up, dan mag dat de rest niet
verdringen:

- `actief` (de kandidaten voor de tegel) sorteert koersen die op de tegel
  mogen vooraan vóór het afkappen op `MAX_ACTIEVE_KOERSEN`.
- `andere_koersen` (de knoppen) doet hetzelfde, zodat de vrouwen-WorldTour
  vóór een ProSeries-koers komt.
- `_build_upcoming` slaat koersen van een pop-up-niveau over die geen eigen
  blok in `races` hebben gekregen; hun etappes zijn dan toch nergens te zien
  en zouden alleen `upcoming_n` opvullen.

### Keuze van de getoonde koers

Mannen en vrouwen koersen vaak tegelijk. De tegel toont er één, gekozen op:

1. eerstvolgende etappedatum
2. grote ronde (`GROTE_RONDES`: Tour, Giro, Vuelta)
3. koers mét hoogteprofiel (`_gpx_rang`)
4. bij gelijke stand de mannen

en pas daarna nog gefilterd op `_mag_op_tegel`. De sleutel staat in
`_keuzesleutel`, apart van de rest zodat de volgorde te testen is.

Het profiel stond eerst bóven de grote ronde, en dat gaf de Renewi Tour
voorrang op de Vuelta zodra de Vuelta-GPX niet binnenkwam: een bestand dat
niet laadt bepaalde zo welke koers de belangrijkste was. Tussen twee koersen
die verder gelijk staan geeft het profiel nog steeds de doorslag. De rondes
van een week bij de vrouwen staan bewust niet in `GROTE_RONDES` — dat zijn
geen grote rondes; wie ze toch voor wil laten gaan verandert de volgorde en
niet die lijst.

De kandidaten zijn tuples van `_keuzesleutel` plus de koers en zijn etappes.
`_races_block` leest die twee daarom van **achteren** (`kandidaat[-2]`,
`kandidaat[-1]`): een sleutel erbij brak anders de uitpakking, en omdat dat
blok zijn fouten per koers afvangt zag je dat niet als een fout maar als een
koers die stilletjes uit de pop-up verdween.

De andere koersen komen terug via `_races_block` → het attribuut `races`: een
lijst met de getoonde koers voorop (`primary: true`) en daarachter hoogstens
`max_other` andere (standaard `MAX_ANDERE_KOERSEN`). De kaart maakt daar
knoppen van bovenin de pop-up; de eerste staat open.

Zo'n blok geeft hetzelfde beeld als de tegelkoers:

- `last_result`, `gc_top`, `points_top`, `kom_top`, `youth_top` — hetzelfde
  als op de tegel. De dagwinst die hier tot 0.24 bij stond is weg: die kwam
  uit de kolom "Prev" bij procyclingstats en cyclingstage geeft geen vorige
  stand per rij.
- `channels` en `channels_detail` — waar die koers te zien is, uit dezelfde
  tv-gids. `_zenders_voor` slaat een koers over die verder dan zes dagen weg
  is, want zo ver kijkt de gids niet vooruit.
- Het profiel komt uit `upcoming` (zie hieronder), inclusief `start_time`,
  `finish_est` en de tussensprint.

### Terugbladeren door de uitslagen

`_build_past` levert het attribuut `past`: de laatst gereden etappes van de
koers op de tegel, van nieuw naar oud, met hoogstens `PAST_RESULT_N` (5)
renners per uitslag. De etappe die al als `last_result` in de attributen
staat wordt overgeslagen; anders stond die dubbel.

**Alleen voor de tegelkoers.** Elke rij draagt `race_key`, dus de kaart kan
het per koersblok uit elkaar houden en het zou per koers kunnen — maar dat
vermenigvuldigt zowel de verzoeken bij cyclingstage als de bytes, en die
zitten al boven de grens van de recorder. Wie het breder wil, begint daar.

`_past_cache` wordt als enige cache **niet** bij een dagwissel geleegd: een
etappe die gereden is verandert niet meer, en juist gisteren is de etappe
waarin het meest wordt teruggekeken. Alleen een uitslag die er ook echt is
komt erin — een pagina die nog leeg was wordt morgen opnieuw geprobeerd.

In de kaart is het één sectie. `uitslagenblok` zet `last_result` als eerste
bladzijde en de rijen uit `past` daarachter; bij één bladzijde tekent het
precies wat `tijdlijst` ook zou tekenen, dus zonder pijlen. Alle bladzijden
staan in de HTML en worden verborgen — de sensor stuurt ze al mee en een
klik hoort niet op het netwerk te wachten. `_bladerknoppen` handelt elke
`.uitslagen` los af, want elk koersblok kan er een hebben.

`past` in `sections` zet alleen de pijlen aan of uit; `result` blijft de
schakelaar voor de uitslag zelf.

### Startlijst als er nog geen uitslag is

Een koers die nog moet beginnen heeft niets te tonen: geen uitslag, geen
klassement. Daar komt de startlijst voor in de plaats — `startlist_top`,
`startlist_riders`, `startlist_teams` en `startlist_out`, op de tegel én op
elk koersblok, en alleen zolang `last_result` leeg is. Zodra er gereden is
verdwijnt hij weer; dat scheelt ruimte in de attributen en de uitslag zegt
meer.

De bron is cyclingstage; zie "De startlijst komt van cyclingstage" verderop
voor de parser, het adres en waarom het rugnummer géén rangorde is.

**Op de tegel hoort `shown_event` en niet `cur`.** Die twee wijken uiteen
zodra de tegel doorrolt naar de volgende koers; met `cur` zou de startlijst
van de vórige koers gepubliceerd worden onder de naam van de nieuwe. Dat is
in 0.26.1 gerepareerd nadat een review het vond.

`_zenders_voor`, `_sprints_voor` en `_startlijst_blok` slikken hun eigen
fouten en geven leeg terug. Dat moet: `_races_block` vangt een uitzondering per blok af
door het hele blok te laten vallen, en een hikje bij wielerflits hoort geen
koers uit de pop-up te laten verdwijnen.

Elk koersblok draagt `jersey`: de kleur van de leiderstrui uit de tabel
`LEIDERSTRUI`, met de procyclingstats-naam als sleutel. Dat is een vaste
lijst en geen bron — PCS geeft truikleuren nergens terug — dus er staan
alleen koersen in waarvan de kleur vaststaat. Een koers die er niet in staat
krijgt `""` en houdt in de kaart de accentkleur. Niets gokken; een
eendaagse koers hoort er sowieso niet in, want die heeft geen klassement.
De kaart kiest zwarte of witte letters op de knop aan de hand van de
helderheid (`tekstOp`), anders is geel onleesbaar.

Een koersblok stuurt géén eigen hoogteprofiel mee. Elke etappe in `upcoming`
draagt een `race_key`, en de kaart pakt daaruit de eerste etappe van die
koers als profiel en de rest als "Komende dagen". Dat scheelt een tweede
profiel in de attributen, en het is meteen de reden dat "Komende dagen" per
koers wordt opgesplitst zodra er meer dan één is — bij één koers blijft dat
overzicht alle koersen door elkaar tonen, zoals eerder.

Omdat dat profiel uit `upcoming` komt, staan `start_time` en `finish_est` op
elke etappe daarin (uit `_fetch_stage_meta`, dus zonder extra verzoek);
anders zou de badge van een pop-upkoers alleen een dag tonen en die van de
tegel ook de tijden. De tussensprint zit er alleen op de **eerste** etappe
van een koers die een eigen blok heeft: dat is de etappe die als profiel
getekend wordt, en elke sprint kost een verzoek bij cyclingstage. De
tegelkoers krijgt hem niet uit `upcoming` — die staat al in de gewone
attributen.

`other_label`, `other_result` en `other_gc` blijven bestaan voor kaarten van
vóór deze opzet; ze herhalen de eerste andere koers met een uitslag. De
meegeleverde kaart tekent ze alleen nog als er één koers is, anders zouden
ze dubbel staan met het eigen blok van die koers.

## Bronnen en URL-patronen

### procyclingstats — historie, sinds 0.25 niet meer in gebruik

Alles in deze sectie beschrijft hoe het wás. De code is in 0.25 verwijderd en
`requirements` in de manifest is leeg; het staat er omdat de reden waaróm die
weg uitgeput is telkens opnieuw wordt gevraagd. Zoek geen van deze functies
in de broncode — ze bestaan niet meer.

#### Het pakket (`procyclingstats==0.2.8` + `cloudscraper` + `curl_cffi`)

**procyclingstats.com staat sinds 23 augustus 2026 achter Cloudflare.** In
het log van die dag: `Kalender van WorldTour mannen ophalen mislukt:
Cloudflare protection detected. Install 'cloudscraper': pip install
cloudscraper`, voor elk niveau, gevolgd door een lege kalender en een
sensor die niet meer laadde.

`cloudscraper` staat daarom in de manifest onder `requirements`. Er hoefde
verder niets aan de code te veranderen: `Scraper._get_session()` in
procyclingstats 0.2.8 doet `import cloudscraper` in een `try` en gebruikt
het vanzelf als het er is (nagekeken in de wheel van pypi, `scraper.py`).
Het staat niet in `requires_dist` van het pakket, dus zonder onze regel komt
het er niet.

**De melding van procyclingstats zegt niet of cloudscraper actief is.**
`_make_request` kijkt alleen of het antwoord een uitdagingspagina is of een
403, en plakt daar onvoorwaardelijk `Install 'cloudscraper'` achter — ook
wanneer cloudscraper wél draait. Uit het log alleen is dus niet te zien of
de bypass ontbreekt of dat hij er niet langs komt, en dat is het verschil
tussen "herstart Home Assistant" en "dit pakket helpt hier niet meer".
Daarom hangt `_fetch_calendar` bij een Cloudflare-fout `_bypass_diag()`
achter de melding: die probeert de import en zegt welke van de twee het is.

Op 23 augustus 2026 bleef de melding staan ná het toevoegen van
cloudscraper, en `_bypass_diag()` bevestigde dat het pakket wél geladen was.
Dat is te verwachten: 1.2.71 is van april 2023 en doet alleen de **headers**
van een browser na, niet de TLS-handdruk. Cloudflare herkent die
vingerafdruk.

### curl_cffi als tweede bypass

`_zet_pcs_sessie()` vervangt daarom `Scraper._get_session()` door een
`curl_cffi`-sessie met `impersonate="chrome"`: die bootst de TLS-handdruk
van Chrome zélf na. Het gebeurt één keer per proces, lui, bovenin
`_fetch_calendar` — de eerste PCS-aanroep van elke ronde.

Dit is een **monkeypatch op andermans pakket**. `_get_session` is interne
code van procyclingstats en kan bij een update verdwijnen; daarom wordt
alles afgevangen en blijft bij twijfel de eigen sessie van het pakket staan.
Ontbreekt `curl_cffi`, dan verandert er niets. `_PCS_SESSIE` bewaart wat er
gebeurd is en komt in `_bypass_diag()` terecht, zodat het log zegt wélke
bypasses er draaiden toen het alsnog misging.

Wat hiervan geverifieerd is: dat het échte `_make_request` van
procyclingstats door de curl_cffi-sessie loopt en HTML teruggeeft (hier
beproefd tegen een bereikbare site). Wat **niet** geverifieerd is: of
Cloudflare de vingerafdruk van curl_cffi doorlaat — daarvoor is
procyclingstats nodig en die laat de proxy niet door. Werkt ook dit niet,
dan is het niet in deze integratie op te lossen en hangt het van het
`procyclingstats`-pakket af.

Verdwijnt de Cloudflare-bescherming weer, dan kan deze patch eruit; hij doet
verder geen kwaad, maar is onderhoud dat we liever niet hebben.

**Op 23 augustus 2026 kwam ook curl_cffi er niet langs.** Het log zei
letterlijk: `cloudscraper 1.2.71 is wél geladen en curl_cffi actief
(impersonate=chrome); procyclingstats komt er ondanks die bypass(es) niet
langs`. Verder gokken op bypasses heeft daarna geen zin meer.

### Wát de bron terugstuurt

`_make_request` gooit dezelfde fout bij `'Just a moment' in response.text`
**en** bij `status_code == 403`, en dat zijn twee heel verschillende dingen:

| wat er terugkomt | betekenis | valt er iets aan te doen |
|---|---|---|
| uitdagingspagina ("Just a moment", `challenge-platform`) | JS-challenge | in principe wel, maar alleen met een echte browser — te zwaar voor HA |
| kale 403, vaak met `Error 1020` | firewallregel of IP-reputatie | nee, niet aan onze kant |

`_pcs_antwoord_diag` doet daarom één verzoek met **dezelfde sessie die het
pakket gebruikt** en logt statuscode, lengte, de Cloudflare-foutcode uit de
body, of er uitdagingstekst in staat, de headers `cf-mitigated`, `cf-ray` en
`server`, en de eerste 160 tekens platte tekst. Alleen bij een
Cloudflare-fout en hoogstens één keer per ronde, dus het kost niets zolang
alles werkt.

Dit is diagnose en geen oplossing: het bepaalt of er nog een weg is, en
zonder dat antwoord is elke volgende stap gokwerk.

**Op 23 augustus 2026 gaf dat antwoord uitsluitsel:**

```
status 403; 5846 tekens; uitdagingspagina (challenge-platform);
cf-ray=a2fa61797ce3d4ca-AMS; server=cloudflare;
begin: "Attention Required! | Cloudflare ... navigator.cookieEnabled ..."
```

Een interstitiële uitdagingspagina met het `cdn-cgi/challenge-platform`-script.
Die deelt pas een clearance-cookie uit nadat er JavaScript is uitgevoerd, dus
geen enkele HTTP-client komt erlangs — ook niet met een perfecte
TLS-vingerafdruk. Alleen een echte browser zou het kunnen, en dat is voor
een dashboardintegratie geen begaanbare weg. **Hiermee is de weg binnen deze
integratie uitgeput**; het hangt van het `procyclingstats`-pakket af, of van
procyclingstats.com dat zijn instellingen versoepelt.

### Niet blijven roepen

Zo'n blokkade kan weken duren. Daarom dempt `_LAATSTE_KALENDERFOUT` de
herhaling: dezelfde fout logt de eerste keer op waarschuwing en daarna op
debug. Dat werkt ook binnen één ronde — vier niveaus die op hetzelfde
stuklopen geven één waarschuwing in plaats van vier. Lukt de kalender weer,
dan wordt de teller geleegd en is de volgende storing weer nieuws.

Het proefverzoek van `_pcs_antwoord_diag` gaat om dezelfde reden alleen bij
een fout die we nog niet gezien hadden: een site die ons weigert hoort niet
elk half uur een extra verzoek te krijgen omdat wij willen weten waarom.


- Kalender: `races.php?year={y}&circuit={c}&class=&filter=Filter`
  - `circuit=1` mannen-WorldTour, `circuit=24` Women's WorldTour (geverifieerd)
  - Kalenderlinks eindigen soms op `/gc` of `/result` → normaliseren naar
    `race/<slug>/<jaar>` met een regex, anders breekt de etappelijst.
- Etappe: `Stage(stage_url)`; bij een **eendaagse** koers staat de info op
  `{url}/result` (zie `_stage_obj`).
- Cols vooraf: `RaceClimbs(f"{stage_url}/route/climbs")` — voorspelbaar adres,
  werkt voor élke koers. Dit is de terugval voor colnamen.
- Startlijst: `RaceStartlist(f"{race_url}/startlist")` — per ploegblok geparsed,
  dus de koppeling renner→ploeg is hier betrouwbaar. `_fetch_startlist` levert
  de rijen (renner, ploeg en hun adressen); `_roster_van` maakt daar de
  renner→ploeg-tabel van die `_repair_rows` gebruikt.
- Ranglijst: `Ranking("rankings/me/individual").individual_ranking(...)`, en
  voor de vrouwen `rankings/we/individual`. Dat vrouwenadres is nooit
  geverifieerd en is met de rest verdwenen.

### Als de kalender geen routeadres geeft (sinds 0.24)

De kalenderpagina heeft per koers een routekolom en een resultatenkolom, en
die zijn **niet altijd gevuld**. In 2026 staan er zes koersen met lege
cellen: Tour of Britain, GP Québec, GP Montréal, het WK, Lombardije en
Parijs-Tours. `_fetch_calendar` valt dan terug op de koerspagina
(`route_url or url`), en dat is een ánder soort pagina.

Dat leverde twee fouten op die geen fout léken:

- **Alleen de etappe van vandaag.** `parse_etappes` las de **eerste** tabel
  op de pagina. Op een routepagina is dat de etappetabel; op een koerspagina
  staat er iets anders vooraan, en één bruikbare rij daarin werd de hele
  etappelijst. Geen uitzondering, geen leeg veld — een koers met precies één
  etappe. Sinds 0.24 worden álle tabellen geprobeerd en wint de rijkste.
- **Geen etappelijst waar er wel een is.** De etappetabel staat een niveau
  dieper, op een adres dat niet af te leiden is: `route-gb-2026` bij de Tour
  of Britain, `route-tdu-2026` bij de Tour Down Under, `spain-route-2026`
  bij de Vuelta. Die afkorting kan niemand raden. **De koerspagina linkt er
  zelf naar**, dus `route_kandidaten` leest de links eruit die onder
  diezelfde koersmap hangen, met "route" vooraan. Hoogstens
  `MAX_ROUTE_KANDIDATEN` (3) worden er echt opgehaald — de menubalk van
  cyclingstage noemt élke koers van de site (268 links op de
  Vuelta-routepagina), dus zonder die padeis is dit een verzoekenregen.

### Drie vormen van een routepagina (sinds 0.27)

Een routepagina kan er op drie manieren uitzien, en alle drie komen voor:

1. **Een etappetabel** — nummer, datum, "start - finish", afstand, terrein,
   met per etappe een adres. Zo staan de grote rondes erop; `parse_etappes`
   leest dit.
2. **Een programmatabel zonder nummerkolom** — datum, "start - finish",
   type, km, hoogtemeters. Zo staat het WK erop: het zijn onderdelen (ITT,
   mixed relay, wegrace) en geen genummerde etappes, en er staat geen enkele
   link in. Daar valt dus niets mee te doen; zie de fixture
   `cyclingstage_wk_2026_canada.html`.
3. **Geen tabel, maar lopende tekst** — `<em>Stage 1</em> – <small>182.5
   kilometres, 1,393 metres of elevation gain</small>` gevolgd door een
   alinea. Zo staat de Tour of Britain erop. `parse_etappes_tekst` leest
   nummer, afstand en hoogtemeters; meer staat er niet.

Bij die derde vorm ontbreekt de **datum per etappe**, en daar rekent de hele
tegelkeuze op. `_datums_verdelen` vult hem alleen aan als er precies zoveel
etappes zijn als koersdagen — dan is er maar één indeling mogelijk en is het
geen gok. Zijn er minder etappes dan dagen, dan zitten er rustdagen tussen
en is niet te zeggen wélke; dan blijft de lijst leeg en valt de koers weg.
Een etappe op de verkeerde dag is erger dan geen etappe.

Er is bij die vorm ook geen etappe-adres. Dat is minder erg dan het lijkt:
de uitslag komt via `_uitslagindex` (de resultatenpagina van de koers noemt
de adressen) en het profiel via de GPX-overzichtspagina.

### Uitslagen buiten de grote rondes (sinds 0.24)

`uitslag_url` eiste `-route/` in het etappeadres. Dat hébben alleen de Giro,
de Tour en de Vuelta: `/vuelta-2026-route/stage-2-spain-2026/`. De andere 46
koersen van de kalender staan als `/tour-down-under-2026/stage-3-tdu-2026/`
en kregen dus **stil nooit een uitslag** — geen fout in het log, gewoon een
lege uitslag.

Nu zijn er twee wegen, in deze volgorde (`_uitslagpagina` in `sensor.py`):

1. **Afleiden uit het etappeadres.** De `-route`-vorm is nagekeken op de
   echte Vuelta-pagina; voor de rest wordt `-results` achter de koersmap
   geplakt, wat gelijk is aan `uitslag_index_url`. Dat is een afleiding en
   geen bron, maar hij kost niets: geen extra verzoek.
2. **Opzoeken op de resultatenpagina van de koers.** Levert weg 1 niets op,
   dan leest `parse_uitslag_index` daar het échte adres per etappenummer.
   Eén verzoek per koers per dag (`_UITSLAGINDEX`, module-breed omdat
   `_cs_fetch_stage` het bron-contract volgt en alleen de etappe meekrijgt);
   `{}` in die cache betekent "vandaag al geprobeerd".

Een **eendaagse** koers heeft geen `stage-N`-pagina en dus geen weg 1; zijn
uitslag staat op zijn resultatenpagina zelf en die wordt direct gelezen.
Vandaar ook de eis dat er `stage-N` in de bestandsnaam staat voordat er iets
wordt afgeleid: zonder die eis leverde `/paris-roubaix-2026/route-pr-2026/`
elke ronde een verzoek op naar een adres dat niet kan bestaan.

**Wat hiervan niet geverifieerd is:** de opmaak van de resultatenindexpagina
zelf — de proxy laat cyclingstage niet door. Wat wél vaststaat is de vórm van
zo'n link: `/vuelta-2026-results/stage-2-spain-results-2026/` staat letterlijk
in de opgeslagen Vuelta-routepagina, en `parse_uitslag_index` vindt hem daar.
De herkenning is daarom zo ruim mogelijk gehouden (elk adres onder de
resultatenmap van déze koers met `stage-N` in het pad). Werkt het niet, zoek
dan in het debuglogboek op "Uitslagoverzicht".

### Terugbladeren: hoe ver, en wat het kost

`past_n` mag sinds 0.24 tot 21 — een hele grote ronde. Het was 10, en de
standaard blijft 3. Wie op etappe 14 van de Vuelta zit en `past_n` op 5 heeft
staan komt tot etappe 8 en niet verder; dat is geen storing maar de
instelling, en het was uit het dashboard niet te zien.

**Verhogen is een ruil.** De attributen zitten in de praktijk al boven de
16 kB van de recorder (zie "Omvang van de attributen"); elke etappe erbij is
ruim 400 bytes en duwt daar verder overheen. De sensor en de kaart blijven
werken — de attributen gaan over de websocket — maar de recorder bewaart ze
dan niet en er is geen historie meer. De verzoeken vallen wél mee: een
gereden uitslag verandert niet meer en `_past_cache` wordt als enige cache
niet bij een dagwissel geleegd.

### Live: welke bron, en waarom dat per organisator is

Nagekeken op 5 september 2026, met een belangrijke beperking: **de proxy in
de ontwikkelomgeving laat geen van deze sites door**, dus dit is
bureauonderzoek op zoekresultaten en op wat er al in `tests/fixtures/` ligt,
niet op opgehaalde pagina's. Elke regel hieronder moet opnieuw worden
nagekeken voordat er code op gebouwd wordt — te beginnen met de `robots.txt`,
zoals bij FirstCycling.

**Er is geen enkele bron die alle koersen live dekt en open is.** Dat is de
kern van het antwoord. Wat er is:

| bron | dekt | vorm | wat we weten |
|---|---|---|---|
| ASO Race Center | Tour, Vuelta, Dauphiné, Parijs-Nice, Parijs-Roubaix, Luik, Flèche, TdF Femmes | `racecenter.{koers}.{tld}/api/{bind}-{jaar}`, JSON, geen sleutel | de etappelijst is bewezen: `racecenter_vuelta_2026_stages.json` is een echte respons. Of de **live**-feed (km-to-go, positie) er ook zo uitziet is **niet** vastgesteld — daar is `/live-stream` of `/api/telemetryCompetitor-{jaar}` voor nodig |
| RCS Sport | Giro, Sanremo, Strade, Tirreno, Lombardije | eigen live-platform | niet onderzocht |
| Flanders Classics | Ronde, Omloop, Dwars, Gent-Wevelgem | eigen live | niet onderzocht |
| Velon | ~25 koersen incl. Tour of Britain 2026 | telemetrie (snelheid, vermogen, cadans, positie) | **B2B**: het gaat naar broadcasters en naar hun eigen app, niet naar een open eindpunt. Geen begaanbare weg voor deze integratie |
| procyclingstats | alles | — | onbereikbaar, zie hierboven |
| FirstCycling | alles | — | `Disallow: /`, klaar |

Dus: **ja, per organisator los, en nee, niet in één klap.** Dat is precies
waar `bronnen.py` voor gemaakt is — een bron per platform, de koers wijst hem
aan. ASO is de meest lonende eerste stap: één parser bedient acht koersen,
waaronder twee grote rondes, en de vorm van het eindpunt staat al vast.

Drie dingen om vooraf te wegen, want ze maken live iets anders dan de rest
van deze integratie:

- **Het verzoekpatroon is een ander.** De kalender is één pagina per dag; een
  live-positie die iets toevoegt wil elke minuut ververst worden. Dat is
  honderden keren zoveel verkeer bij een site die daar niets voor terugkrijgt.
  `live_scan_minutes` staat op 5 en dat is voor een stip aan de lage kant —
  wie dat omlaag wil moet zich afvragen of de bron dat mag merken.
- **Een organisatorfeed ligt eruit op het slechtste moment.** Precies tijdens
  de etappe staat er de meeste druk op. Degraderen moet dus: geen stip is
  goed, een verkeerde stip niet.
- **Niets schatten.** De positie afleiden uit starttijd en afstand is
  verleidelijk en verboden. Het tijdschema (`stage-{n}-times.htm`) geeft wél
  een verwachte passeertijd per punt; daar valt een stip "volgens schema" uit
  te tekenen, maar dan moet de kaart er ook bij zetten dat het een
  voorspelling is en geen meting.

### De live-stip heeft geen bron meer

`_fetch_live` bouwde `procyclingstats.com/{stage_url}/live` en las daar "KM
to go" uit. Sinds 0.19 is `stage_url` een cyclingstage-adres, dus dat werd
letterlijk `procyclingstats.com/https://www.cyclingstage.com/...//live`: een
verzoek dat nergens op sloeg en tijdens een etappe elke vijf minuten opnieuw
ging. Met het juiste adres zou het trouwens ook niets opleveren — PCS zit
achter de uitdagingspagina.

Cyclingstage heeft geen vervanger: het woord "live" komt op de etappepagina
nul keer voor. Sinds 0.22.2 is de aanroep dus weg en blijven
`live_km_to_go`, `live_avg_speed`, `live_status` en `live_url` leeg; de
sleutels staan er nog zodat een oudere kaart niet struikelt. De positie
schatten uit starttijd en afstand zou precies het verzinnen zijn dat dit
project niet doet.

Het tijdschema (`stage-{n}-times.htm`) geeft wél per punt een verwachte
passeertijd. Daar zou een stip "volgens schema" uit te tekenen zijn, maar dat
is een voorspelling en geen meting; wie dat wil moet het als zodanig
benoemen in de kaart.

De status blijft wel op `LIVE` staan — die komt uit de starttijd, en die
heeft cyclingstage.

**Dezelfde fout zit nog in de col-namen.** `_fetch_race_climbs` en
`_fetch_stage_climbs` geven een cyclingstage-adres door aan `RaceClimbs`
en `Stage` van procyclingstats, die een PCS-pad verwachten. Ze vangen hun
eigen fouten af, dus het valt niet op, maar het zijn verzoeken die niet
kunnen slagen. Ze horen bij het opruimen van de laatste PCS-resten.

### Bronnenregister: koers voor koers erbij

`bronnen.py` is het scharnier voor koersen die cyclingstage niet heeft. Het
bevat **geen parsers** — alleen het register en het contract.

Een bron levert `etappes(koers)`, `uitslag(etappe, result_n, gc_n)` en
optioneel `kalender(jaar)`. `sensor.py` meldt cyclingstage aan als
`STANDAARD` en `_event_stages`/`_fetch_stage` zijn nog maar dispatchers: ze
zoeken de bron op (`bron` op de koers of de etappe, anders de standaard) en
vangen alles af wat eruit komt. Een organisatorsite die eruit ligt levert
dus een lege lijst of `_lege_uitslag`, nooit een uitzondering naar boven.

`_event_stages` zet `bron` op elke etappe die terugkomt, zodat `_fetch_stage`
later niet hoeft te raden. Een bron die etappes van een ánder platform
doorgeeft mag die sleutel zelf zetten; wat er al staat blijft staan.

`EXTRA_KOERSEN` is voor koersen die in geen enkele kalender voorkomen. Die
lijst is bewust **leeg**: een koers erin zetten zonder bron die hem kan
bedienen levert een koers zonder etappes op, en die verdwijnt stil weer.

Een koers toevoegen is dan:

1. `robots.txt` van de organisator nalezen. `Disallow: /` betekent klaar.
2. Een echte pagina opslaan, parser ernaast, HTML in `tests/fixtures/`.
3. `registreer(Bron(...))`.
4. De koers in `EXTRA_KOERSEN`, of `bron` op zijn kalenderregel als hij wél
   in de kalender staat maar zijn etappes elders vandaan moeten komen.

`tests/test_bronnen.py` mag met een verzonnen bron werken: dat test óns
contract, niet het lezen van andermans pagina's. Voor een échte bron blijft
gelden dat er opgeslagen HTML aan te pas komt.

Let op de importnaam in tests: `cycling_next_race.bronnen` via de fixture
`bronnen_mod`. Het pad `custom_components.cycling_next_race.bronnen` levert
een tweede exemplaar met een eigen register op, en dan meldt een test een
bron aan die `sensor.py` nooit ziet.

### Wat de robots.txt van onze bronnen zegt

Op 7 september 2026 opgehaald door de eigenaar (de proxy hier laat ze niet
door) en letterlijk bewaard in `docs/robots/`. Deze controle was er nooit
geweest, terwijl FirstCycling er wél op is afgewezen — dat was een gat.

**Wielerflits: in orde.** De `User-agent: *`-groep noemt een lijst paden
(`/wp-admin/`, feeds, archief, URL's met parameters) en `Disallow: /` staat
er niet bij. De tv-gids op `/nieuws/wielrennen-op-tv/` valt onder geen enkele
regel. `GPTBot` en `CCBot` zijn expliciet geweerd en `ia_archiver` ook, maar
onze user-agent is geen van drieën — en anders dan bij FirstCycling staat
ClaudeBot er niet bij naam in. Er staat één `Crawl-delay: 5`; die hangt in
het bestand onder het `ia_archiver`-blok en geldt formeel dus alleen daarvoor,
maar het is de enige uitspraak over tempo die de site doet en één verzoek per
dag zit daar ver onder.

**Cyclingstage: geen enkele actieve regel raakt ons, maar lees verder.** Het
bestand opent met:

```
# Deny all robots that we do not specifically want to allow
#User-agent: *
#Disallow: /
```

Die twee regels zijn **uitgecommentarieerd**. Er is dus geen actieve
`*`-groep, en onze user-agent matcht geen van de acht groepen die er wél
staan (MJ12bot, ias_crawler, Twitterbot, twee Google-bots, slurp, bingbot,
googlebot). Volgens het protocol betekent dat: geen restrictie. De
kalenderpagina, de routepagina's, de etappeteksten, de uitslagen, de
resultatenindex en de startlijst raken geen enkele regel — die zijn zelfs
voor googlebot toegestaan.

**Maar `/images` is in élk toegelaten blok verboden.** ias_crawler,
Mediapartners-Google, slurp, bingbot en googlebot krijgen allemaal
`Disallow: /images`. En daar hangen twee dingen van ons:

| ons adres | wat het levert |
|---|---|
| `www.cyclingstage.com/images/{slug}/{jaar}/stage-{n}-times.htm` | het tijdschema, en daarmee de tussensprint |
| `cdn.cyclingstage.com/images/{slug}/{jaar}/stage-{n}-parcours.gpx` | het hoogteprofiel |

Formeel geldt die regel niet voor ons, want we matchen geen groep. Maar het
is een consistent signaal over precies dat pad, en de uitgecommentarieerde
kopregel laat zien dat de eigenaar ooit een allowlist wilde. Daar staat
tegenover dat dit een WordPress-site is en `Disallow: /images` daar een
sjabloonregel is die bedoeld is om afbeeldingen niet te laten indexeren — en
dat cyclingstage de GPX-bestanden zélf aanbiedt op een eigen
overzichtspagina, om te downloaden.

**Besluit van de eigenaar (7 september 2026): laten staan, maar netter
gedragen.** Formeel is er geen regel die ons verbiedt, het gaat om één
verzoek per etappe per dag, en cyclingstage biedt die GPX-bestanden zelf aan
om te downloaden. Wat er wél veranderd is: de user-agent. Die luidde
`Mozilla/5.0 (HomeAssistant CyclingNextRace)` — een browserstring die de
beheerder van een bron niets geeft om op te reageren. Sinds 0.26.2 is het
`Mozilla/5.0 (compatible; CyclingNextRace/{versie};
+https://github.com/vossov/cycling-next-race)`: herkenbaar, met een adres
waar te zien is wat dit is. Wie zich op een grens beroept die formeel niet
voor hem geldt, hoort zich in elk geval kenbaar te maken.

**Dat neemt de onzekerheid niet weg.** Wat hier vaststaat: het is geen `Disallow: /` zoals bij
FirstCycling, en het is ook niet niks. Wie hierop terugkomt: de bestanden
staan in `docs/robots/`, de afweging staat hierboven, en het gaat om het
hoogteprofiel en de tussensprint — niet om de rest van de integratie.

### Wat "verboden" betekent in dit project

Vastgelegd op 7 september 2026, na een discussie waarin dit te ver was
doorgeslagen.

**De regel: wat niet expliciet verboden is, mag.** Een `Disallow` die op onze
user-agent en op ons pad slaat is een verbod en daar houden we ons aan. Een
afwezige regel, een regel voor een andere bot, een regel op een ander
subdomein of een uitgecommentarieerde regel is géén verbod.

Waarom die grens zo strak getrokken is: bij het tegenovergestelde
uitgangspunt — "als het niet uitdrukkelijk is toegestaan, laat het" — mag
niets meer. Vrijwel geen enkele site geeft expliciet toestemming, dus dan
valt elke bron af en houdt deze integratie op te bestaan. Dat is geen
zorgvuldigheid meer maar verlamming.

Wat dat concreet betekent voor de drie gevallen die we tegenkwamen:

| geval | uitkomst |
|---|---|
| FirstCycling: `User-agent: *` met `Disallow: /`, plus ClaudeBot bij naam | **verboden**, en dat blijft zo |
| Cyclingstage: `Disallow: /images` in de blokken van googlebot en anderen, geen actieve `*`-groep | **toegestaan** — die regels gelden voor die bots, niet voor ons |
| ASO: `Disallow: /api` op `www.lavuelta.es`, geen robots.txt op `racecenter.lavuelta.es` | **toegestaan** — robots.txt geldt per host, dat is de standaard en geen technicality |

Wat wél van ons wordt gevraagd, juist omdat we ons op die grens beroepen:
een herkenbare user-agent met een adres erin (zie `UA` in sensor.py), niet
vaker ophalen dan nodig, en netjes degraderen als een bron eruit ligt. Wie
zich op de letter beroept, hoort zich ook aan de rest van de omgangsvormen
te houden.

De bestanden staan in `docs/robots/`, met per bron wat er precies staat.

### FirstCycling is uitgesloten (robots.txt)

Op 27 augustus 2026 nagekeken als kandidaat om cyclingstage te vervangen of
aan te vullen: het is qua opzet de dichtste open tegenhanger van
procyclingstats (`race.php?t={niveau}&y={jaar}` voor de kalender,
`race.php?r={koers}&y={jaar}` voor een koers), het kent UCI-niveaus, het
punten-, berg- en jongerenklassement, ploegen en profieltypes, en het heeft
de héle UCI-kalender in plaats van een redactionele selectie. Precies alles
wat we bij de overstap naar cyclingstage hebben ingeleverd.

**Hun `robots.txt` verbiedt het:**

```
User-agent: ClaudeBot
Disallow: /

User-agent: *
Disallow: /
```

De hele site, voor elke geautomatiseerde bezoeker, met ClaudeBot (en GPTBot,
CCBot, Google-Extended) er apart bij naam in. Daarmee is het klaar. Niet
omdat een scraper technisch zou falen — hij zou werken — maar omdat de
eigenaar het zo duidelijk mogelijk heeft opgeschreven.

Redeneer er niet omheen met "wij zijn geen crawler, wij halen één pagina per
half uur op voor één dashboard". Die vraag is bij procyclingstats al gesteld
en eerlijk beantwoord; het antwoord verandert niet doordat het ons nu
slechter uitkomt.

**Dezelfde maat geldt voor de bronnen die we wél gebruiken.** Wie hier langs
komt en de `robots.txt` van cyclingstage, wielerflits of racecenter nog niet
heeft nagekeken: doe dat. Staat daar hetzelfde, dan is dat een probleem dat
we moeten weten, niet een probleem dat we moeten wegkijken.

### cyclingstage.com wordt de hoofdbron

Nu procyclingstats onbereikbaar is en die weg uitgeput, gaat de kalender —
en op termijn de rest — naar cyclingstage. Die bron leverde al de GPX, de
tijdschema's en de etappeteksten, en is vanaf een gewone
thuisverbinding bereikbaar (bewezen: in het log van 21-22 augustus staat
geen enkele cyclingstage-fout en de attributen bevatten `elevation`).

De nieuwe parsers staan in `cyclingstage.py`, los van `sensor.py`, zodat de
oude PCS-code er tijdens de overgang naast blijft staan. Ze zijn beproefd op
**echte HTML** in `tests/fixtures/` — opgeslagen in een browser, want de
proxy in de ontwikkelomgeving laat cyclingstage niet door.

**De kalenderpagina geeft het adres van elke koers mee.** Dat is de winst:
`/uci/cycling-calendar-{jaar}/` heeft één tabel per maand met datum, naam,
land, route-adres en resultaten-adres. Geen sjablonen meer raden — precies
dat raden kostte het profiel van de Vuelta en de colnamen van de Giro.

Twee dingen die cyclingstage **niet** heeft, en die de opzet veranderen:

- **Geen UCI-niveaus.** "WorldTour", "ProSeries" en "UWT" komen nul keer
  voor op de kalenderpagina. `levels` kan daar dus alleen nog mannen en
  vrouwen onderscheiden. Dat gaat wel betrouwbaar: de naam (`Donne`,
  `Femmes`, `Femenina`, `Women`, `(w)`) en het adres (`-women`, `-femmes`,
  `-donne`) zeggen het allebei, onafhankelijk van elkaar.
- **Het is een redactionele selectie.** Boven de tabel staat het met zoveel
  woorden: "the races we are passionate about". 49 koersen in 2026, waarvan
  11 bij de vrouwen. Voor de mannen is dat vrijwel de hele WorldTour (Polen,
  Denemarken en Guangxi ontbreken); bij de vrouwen ontbreken alle rondes van
  een week. Wat er niet in staat had ook geen profiel en geen tijdschema, dus
  het zou toch leeg blijven — maar het is een echt verlies en het hoort in
  de README te staan.

De routepagina van een koers (`/vuelta-2026-route/`) heeft één tabel met
nummer, datum, "start - finish", afstand en terreintype, en per etappe het
eigen adres. Rustdagen staan er als eigen rij in, met een lege nummerkolom
en `rest day` over drie kolommen; `parse_etappes` slaat die over, want de
rest van de integratie rekent elke regel als een etappe. Het nummer komt uit
de tabel en niet uit een teller, dus rustdagen verschuiven niets.

Op de etappepagina zelf staat in gewone zinnen wat we tot nu toe bij
procyclingstats haalden: "starts at 14:40 and the race is expected to finish
around 17:30" en "2,953 metres of elevation gain". De verwachte finishtijd
is zelfs beter dan wat we hadden — die werd geschat uit afstand en profiel
(`_finish_est`), en staat hier gewoon. `parse_etappe_meta` leest die drie;
de colnamen komen uit `_fetch_stage_names` in `sensor.py`, dat al op deze
teksten gebouwd is en blijft.

De resultatenpagina (`/vuelta-2026-results/stage-2-spain-results-2026/`) heeft
géén tabel: de uitslag staat als `<h2>`-kop met een `<p>` eronder, regels
gescheiden door `<br>` — `1. Matthew Brennan (gbr) 4:47:47`. `parse_blokken`
leest elk zo'n blok, `parse_uitslag` kiest daaruit. Een blok telt alleen als
de nummering 1..n is zonder gaten; een alinea die toevallig met "1." begint
is geen uitslag.

Drie dingen die daar anders zijn dan bij procyclingstats:

- **Geen ploeg, alleen een landcode.** Een land is geen ploeg, dus het gaat
  als `country` mee en niet als `team`. De kaart toont het als terugval waar
  eerst de UCI-ploegcode stond. `_fetch_team_abbr`, `_abbr_cache` en
  `MAX_PLOEGCODES_PER_RONDE` hebben daarmee geen bron meer.
- **Geen punten-, berg- en jongerenklassement.** Op 23 augustus 2026 hebben
  `/vuelta-2026-points-classification/` en `/vuelta-2026-kom-classification/`
  alleen de puntenverdeling, met de mededeling dat de standen "in a table
  during La Vuelta" komen en "You'll find the rankings under results" — en op
  de resultatenpagina staan ze niet. `_KLASSEMENTEN` in `cyclingstage.py`
  herkent ze op de kop, dus zodra ze verschijnen lopen ze mee zonder
  codewijziging.
- **Geen dagwinst.** Die werd berekend uit de "Prev"-kolom; cyclingstage
  geeft geen vorige stand per rij. `_rank_maps` en `_gain_*` hadden daarmee
  geen bron meer en zijn in 0.25 verwijderd.

**De kop van het klassement liegt.** Op de pagina van etappe 2 staat "GC
after stage 1" boven het klassement ná die etappe (Pogacar eerste, Brennan
derde — precies wat het artikel beschrijft). Dat nummer telt daarom alleen
om te zien wélk klassement het is, nooit om te bepalen bij welke etappe het
hoort.

`uitslag_url` leidt het resultatenadres af uit het etappeadres
(`stage-2-spain-2026` → `stage-2-spain-results-2026`); nagekeken tegen de
echte pagina. Lukt dat ooit niet, dan staan ze allemaal op
`uitslag_index_url`.

Let op de typefouten op de site: etappe 2 van de Vuelta staat als `hils` in
plaats van `hills`, en bij de Tour de France Femmes staat in de kalender een
link die geen adres is (`http://Tour de France Femmes 2026`). Allebei
opgevangen, allebei met een test.

Het datumformaat verdient aandacht: `1`, `20-25` of `4/28-3`. De tabel staat
onder de maand waarin de koers **eindigt**; begint hij in een eerdere maand,
dan staat die maand ervoor. Zonder dat voorvoegsel loopt de Vuelta (`8/22-13`
onder September) van 22 september tot 13 september — achteruit.

### cyclingstage.com

| Doel | Patroon |
|---|---|
| GPX grote rondes | `cdn.../images/{slug}/{y}/stage-{n}-parcours.gpx` |
| GPX overige + vrouwen | `cdn.../images/{slug}/{y}/stage-{n}-route.gpx` |
| GPX eendaags | `cdn.../images/{slug}/{y}/route.gpx` |
| GPX-overzicht per koers | `www.../{slug}-{y}-gpx/` |
| Tijdschema (tussensprint) | `www.../images/{slug}/{y}/stage-{n}-times.htm` |
| Etappetekst (colnamen, finishtijd) | per koers een sjabloon, zie `CYCLINGSTAGE_ROUTE` |

**Sinds 0.26.4 komt het GPX-adres van de etappepagina zelf.** Die noemt het
gewoon (`https://cdn.cyclingstage.com/images/vuelta-spain/2026/stage-4-route.gpx`)
en wordt toch al opgehaald voor de colnamen, dus het kost geen verzoek —
`_etappe_html` deelt hem tussen `_gpx_uit_etappe` en `_fetch_stage_names`.

Dat was nodig omdat de gebouwde adressen hieronder **fout zijn voor de
Vuelta**: de koersslug is `vuelta`, maar de map van de plaatjes heet
`vuelta-spain`. Beide vaste adressen gaven daar een 404, en het profiel hing
volledig op de terugval via de overzichtspagina. Op 7 september 2026
nagemeten met `images/vuelta/2026/stage-19-times.htm` — bestaat niet.

**Dat raakt ook het tijdschema.** `times_url()` bouwt zijn adres op dezelfde
manier en is dus voor de Vuelta net zo fout; de tussensprint komt daar niet
binnen. De etappepagina noemt geen `times.htm`-link, dus daar is die
oplossing niet te herhalen. Wie dit wil repareren heeft de juiste map nodig
— vermoedelijk `vuelta-spain`, maar dat is niet nagekeken.

**De gebouwde adressen hieronder zijn een aanname over de bestandsnaam én
over de map, geen bron.** Wijkt
cyclingstage er voor één koers van af, dan blijft het profiel leeg zonder dat
er iets kapot lijkt — de melding "de GPX van de Vuelta doet het niet" was van
hieruit niet na te trekken, juist omdat er geen fout uit komt. Levert geen
enkel vast adres iets op, dan haalt `_fetch_gpx_index` de GPX-overzichtspagina van
die koers op (`vuelta-2026-gpx`, `giro-2026-gpx`, `tour-de-france-2026-gpx` —
de cyclingstage-slug plus het jaar) en leest daar het échte adres uit. Het
etappenummer komt uit de **bestandsnaam** en niet uit de linktekst: die is
opgemaakt en verschilt per koers, het pad niet. Adressen van een ander jaar
vallen af, want de pagina linkt ook naar eerdere jaargangen.

Die terugval kost hoogstens één verzoek per koers per dag
(`_gpxindex_cache`), en `gpx_used` in de attributen zegt welk adres het
uiteindelijk werd — leeg betekent dat ook de overzichtspagina niets opleverde.

De etappetekst-adressen volgen **geen** vast patroon. Voorbeelden:
`tour-de-france-2026-route/stage-18-tdf-2026/` tegenover
`tour-de-france-femmes-2026/stage-2-tdf-2026-women/` tegenover
`giro-women-2026/stage-5-route-ita-2026/`. Daarom een sjabloon per koers.

`GPX_OVERRIDE` bovenin laat handmatig een GPX-adres per koers instellen; die
gaat vóór op de automatische adressen.

### wielerflits.nl

`https://www.wielerflits.nl/nieuws/wielrennen-op-tv/` — dagoverzicht met per
koers de zenders en tijden. Toont ~6 dagen vooruit, dus alleen ophalen bij
`days_until <= 6`.

**Deze parser draaide tot 0.26.3 volledig op verzonnen HTML** — als enige in
het project. De fixture `wielerflits_tv_2026-09-07.html` legde meteen drie
dingen bloot die geen van alle een fout in het log gaven:

1. **De koppeling was al sinds 0.19 stuk.** `_channels_from` deed
   `re.match(r"race/([^/]+)/(\d{4})", race_url)` — een procyclingstats-pad.
   Sinds de overstap naar cyclingstage komt daar een heel ander adres
   binnen, dus die match faalde altijd en élke koers kreeg een lege lijst.
   Dezelfde soort fout als de live-stip in 0.22.2, en net zo onzichtbaar:
   geen zenders ziet er hetzelfde uit als "vandaag niets op tv".
2. **Een eendaagse koers kon nooit zenders krijgen.** De regex eiste
   `/wielerkalender/{slug}/etappes/{n}/`, maar zo'n koers staat als
   `/wielerkalender/{slug}/startlijst`. Dat trof alle monumenten, alle
   klassiekers, Québec, Montréal, Lombardije en Parijs-Tours.
3. **Koppelen op slug gaf verkeerde zenders.** `giro` is een prefix van
   `giro-della-toscana-…` en `tour-de-france` van
   `tour-de-france-femmes-we-2026`; die twee paren staan letterlijk naast
   elkaar op de opgeslagen pagina. De Giro d'Italia kreeg zo de
   uitzendtijden van de Giro della Toscana — en verkeerde data is erger dan
   geen data.

De koppeling gaat daarom op **naam plus geslacht** (`_zelfde_koers`). Twee
sites schrijven een koersnaam anders — wij hebben "Grand Prix de Québec" uit
de cyclingstage-kalender, wielerflits schrijft "Grand Prix Cycliste de
Québec" — dus worden de namen op woordniveau vergeleken: de ene verzameling
moet in de andere passen, met minstens twee woorden zodat een losse "Tour"
niet overal in past. Het geslacht is wat de Tour en de Tour Femmes uit
elkaar houdt, want op woordniveau is de eerste een deelverzameling van de
tweede. Het komt uit de slug (`-we-`) én uit "Women Elite" op de regel
erna — twee onafhankelijke signalen, net als bij de kalender.

De eis dat er `/etappes/{n}/` of `/startlijst` in het adres staat sluit de
"Lees meer over"-tags onderaan de pagina uit; die linken naar
`/wielerkalender/{slug}` zonder achtervoegsel en zouden anders de tekst
erna als zenders opleveren.

Alleen uitzendingen met een Nederlandse vlag tellen mee. Op 7 september 2026
had etappe 19 er drie — HBO Max (BE+NL), Sporza online (alleen BE) en VRT1
(BE+NL) — en dat maakt de fixture een goede test voor dat filter. Let ook op
de vlag vóór de koersnaam: dat is het land van de kóérs, niet van de
uitzending.

## Valkuilen die al veel tijd hebben gekost

**PCS-namen schuiven op.** `TableParser.rider_name` verzamelt álle rennerlinks
van een tabel als één platte lijst en plakt die positioneel op de rijen, terwijl
`time` en `team_name` per rij worden gelezen. Eén rij met een extra rennerlink
en alle namen daarna staan verkeerd. Twee reparaties, allebei nodig:
`_row_names()` leest namen per rij uit dezelfde HTML, en `_repair_rows()`
corrigeert op basis van de ploegkolom met de startlijst als referentie.
`_name_key()` maakt de vergelijking onafhankelijk van de volgorde van voor- en
achternaam.

**De kolom "Time won/lost" is onbruikbaar.** PCS vult die met JavaScript; in de
opgehaalde HTML staat `..`. Dagwinst wordt daarom berekend door de stand van de
vorige etappe op te halen als `{positie: waarde}` en te koppelen via de
"Prev"-kolom. Dus **op positie koppelen, nooit op naam** — dat is precies de
kolom die kan verschuiven.

**Downsampling moet vormbehoudend.** Simpel elk zoveelste GPX-punt pakken laat
scherpe toppen verdwijnen (tot 235 m fout bij 45 punten). `_lttb()` lost dat op.

**Korte klimmen.** `_detect_climbs` heeft naast `min_gain=140` een tweede regel
voor kort en steil (`steep_gain=50`, `steep_grad=4.0`, `steep_len=0.5`), anders
mist hij bijvoorbeeld de Butte Montmartre. En het zoeken naar de top moet
doorlopen tot voorbij `win_km`, anders mist een korte klim zijn eigen top.

**Geen GPX = geen profiel.** Voor sommige koersen (San Sebastián, Lombardije,
Ronde van Polen) bestaat publiek geen GPX — gecontroleerd bij cyclingstage,
de organisatiesite, velowire en La Flamme Rouge. Niet reconstrueren.

## Testen

De sandbox/CI kan **procyclingstats.com, cyclingstage.com en wielerflits.nl
niet bereiken**. Verifieer daarom zo:

- Pure functies: `pytest tests/` (stubt Home Assistant, geen netwerk nodig).
- Parsers: voed ze HTML die je met een webfetch hebt opgehaald, niet verzonnen
  HTML — verzonnen HTML heeft al twee keer een echte bug gemaskeerd.
- JS-templates: brace-matching de functie `P` uit de YAML halen en met Node
  draaien tegen synthetische attributen; controleren op `NaN`, `undefined` en
  of de uitvoer met `<svg` begint en op `</svg>` eindigt.
- `python3 -m py_compile` na elke wijziging.
- Echte verificatie gebeurt pas in een draaiende Home Assistant.

## Omvang van de attributen

De recorder weigert attributen boven `MAX_STATE_ATTRS_BYTES` (16 kB) en logt
daarbij bij **elke update** een waarschuwing; de volledige state gaat
bovendien over de websocket naar élke verbonden client. De sensor en de kaart
werken gewoon door — de attributen bereiken de kaart wel — maar de recorder
bewaart ze niet, dus er is geen historie van.

**Reken het na, schat het niet.** Hier stond jarenlang "ruwweg 4 kB per
koersblok, in de praktijk zo'n 28 kB". Dat was te laag. `python3
tools/meet_attributen.py` bouwt een attributenset met dezelfde vorm en
realistische inhoud en meet hem per post; onderhoud dat bestand mee als de
vorm van de attributen verandert. **Het telt UTF-8 bytes en geen tekens** —
de recorder doet dat ook, en met diakrieten in rennernamen (Raúl García
Pierna, Iñigo, Jørgen) scheelt dat honderden bytes de verkeerde kant op.
Gemeten op 6 september 2026, met de standaardinstellingen en de rijen zoals
cyclingstage ze sinds 0.25 levert:

| post | bytes | wat erin zit |
|---|---:|---|
| `upcoming` | 13 189 | 10 etappes × (profiel van 60 punten + tot 4 cols) |
| `races` | 8 908 | 2 blokken × 5 lijsten van 10 renners; het primaire blok draagt géén uitslagen (die staan al in de gewone attributen) |
| `elevation` | 2 395 | 200 punten van de getoonde etappe |
| `past` | 1 681 | 3 etappes × 5 renners |
| de vijf lijsten op de tegel | 3 845 | uitslag, algemeen, punten, berg, jongeren |
| `other_result` + `other_gc` | 1 174 | herhaling van het eerste andere koersblok, voor kaarten van vóór 0.11 |
| **totaal** | **33 327** | ruim het dubbele van de grens |

**Onder de 16 kB komen kan, maar niet met één knop.** Ook gemeten:

| opstelling | bytes |
|---|---:|
| standaard | 33 327 |
| `past_n` op 21 (een hele grote ronde) | 43 443 |
| `max_other` op 1 | 28 936 |
| `upcoming_n` op 6 | 28 067 |
| `upcoming_n` 6 + `max_other` 1 | 23 676 |
| alle knoppen zuinig: `upcoming_n` 4, `max_other` 1, `past_n` 2, 5 renners overal | **15 964** |

Die laatste past net, met weinig marge, en levert een merkbaar kaler
dashboard op: vier komende dagen in plaats van tien, één koers naast de
getoonde, en halve klassementen.

**Weeg eerst wat het oplevert.** Het enige dat je wint is dat de recorder de
attributen bewaart. Dit zijn geen meetwaarden waar je een grafiek van trekt —
het zijn uitslagen, profielen en tv-tijden, en die haal je bij de bron. Voor
wie alleen van de waarschuwing af wil is de goedkope weg dan ook de sensor
uit de recorder houden (zie de README); dat kost niets op het dashboard.
Zichtbaar inleveren om historie te bewaren die niemand opvraagt is de
verkeerde ruil.

Twee dingen die wél bewust klein gehouden zijn en dat moeten blijven:

- **Een koersblok draagt geen hoogteprofiel.** Dat komt uit `upcoming` via
  `race_key`. Zou elk blok zijn eigen profiel meesturen, dan was `races`
  ruwweg dubbel zo zwaar.
- **De profieltjes in "Komende dagen" staan op 60 punten.** Ze stonden op
  150; dat bracht de state op ruim 34 kB en het verschil is niet te zien —
  die profieltjes zijn maar een paar pixels hoog.

`level` op elke etappe in `upcoming` en op elk blok in `races` kost een stuk
of vijftien bytes per stuk — een paar honderd in totaal, en het alternatief
(de kaart laten raden welk niveau een koers heeft) bestaat niet.

Een niveau erbij kost niets zolang er niet méér koersen in beeld komen:
`max_other` begrenst het aantal blokken en `upcoming_n` het aantal etappes.
Wat het wél kost zijn verzoeken bij cyclingstage — een kalenderpagina per
jaar per dag, en een etappelijst per koers die in het venster valt.

## Wat er sinds 0.25 niet meer is

Alles wat via procyclingstats liep is eruit: de startlijst en de ranglijst
die hem ordende (de startlijst is in 0.26 teruggekomen van cyclingstage, zie
hieronder), de officiële ploegcodes, de dagwinst uit de kolom "Prev",
het naamherstel, de colnamen en de colcategorie, en de Cloudflare-bypass
(cloudscraper plus curl_cffi) die het nog probeerde. `requirements` in de
manifest is daarmee **leeg**.

Waarom het eruit moest en niet bleef staan "voor als de site weer opengaat":
elke functie ving zijn eigen fouten af, dus er kwam niets in het log. Wat er
overbleef waren verzoeken die elke ronde op een 403 stukliepen, en drie
pakketten die Home Assistant bij elke start installeerde voor code die niets
kon opleveren. Een dood pad dat er onschuldig uitziet is erger dan een leeg
veld dat je ziet.

De attribuutsleutels blijven bestaan en blijven leeg (`startlist_top`,
`startlist_quality`, `team_code`, `gain_s`), zodat een kaart van vóór deze
versie er niet over struikelt — dezelfde lijn als bij de live-stip in
0.22.2. De optie `start_n` is wél weg: een knop in het instelscherm die
niets doet is verwarrender dan een knop die later terugkomt.

Terughalen begint in de geschiedenis: `git log -S "_fetch_startlist" --
custom_components`. Maar de bron is niet procyclingstats — die weg is
uitgeput. Een startlijst hoort van een bron te komen die wél opendoet, en
dat is een parser met opgeslagen HTML in `tests/fixtures/`, zoals elke
andere bron in dit project.

## De startlijst komt van cyclingstage (sinds 0.26)

**De aanname in 0.25 dat cyclingstage geen startlijst heeft, was fout.** Die
klopte voor de resultatenpagina; de koers heeft er een eigen pagina voor, en
die is rijker dan wat procyclingstats gaf. Zie
`tests/fixtures/cyclingstage_vuelta_2026_riders.html` — de echte pagina, door
de eigenaar in een browser opgeslagen omdat de proxy hier cyclingstage niet
doorlaat.

Per ploeg één `<div class="block">` met de ploegnaam in een `<i>` en daarna
de renners met hun rugnummer, gescheiden door `<br>`:

```
<div class="block">
<i>Visma | Lease a Bike</i><br>
31. Wout van Aert<br>
36. <del datetime="2026-09-05T14:43:03+00:00">Christophe Laporte</del><br>
```

Dus: **ploeg, rugnummer en wie er is uitgevallen** — dat laatste had PCS
niet. Wat er níét staat: een renner-adres, een land, een ploegcode, en welke
renner de kopman is.

### Het rugnummer is geen rangorde

Dit is de verleiding waar deze parser omheen moet. Roglic heeft 1, Pogacar
11, Mas 21 — het ligt voor de hand daar "kopman" van te maken en de lijst zo
te ordenen zonder externe ranglijst. Gemeten op de opgeslagen startlijst:

- bij **22 van de 23 ploegen** staan de nummers x2 tot en met x8 strikt
  alfabetisch op achternaam. Die zeven dragen dus nul informatie.
- alleen het eerste nummer van een ploeg is er bij 18 van de 23 ploegen uit
  getild. Dat is het enige signaal — en het dekt de lading niet: Lidl-Trek
  gaf Mads Pedersen juist het láátste nummer van zijn blok (88), en Visma
  heeft helemaal geen aangewezen kopman.
- er is geen UCI-regel die zegt dat het eerste nummer naar de kopman gaat;
  het is een gewoonte die per organisator verschilt.

Vandaar dat het veld `bib` heet en niet `rank`, dat `startlijst_rijen` op
rugnummer sorteert en dat zo benoemt, en dat de kaart er "per ploeg op
rugnummer" bij zet. Een `rank` van 1 tot 23 zou een ranglijst suggereren die
niemand heeft opgesteld.

### Twee valkuilen die op de echte pagina zitten

Allebei gevonden door de parser tegen de opgeslagen HTML te draaien, allebei
met een test erbij:

- **Een ploegnaam kan zelf een nummer bevatten.** "Pinarello Q36.5" laat een
  regex die in de hele bloktekst naar `NN.` zoekt een 185e renner vinden:
  rugnummer 36, naam "5". Dat nummer bestáát al (Laporte van Visma), dus het
  valt niet eens op als dubbel. Daarom wordt de `<i>`-regel er eerst
  afgeknipt.
- **De opmaak van een rennerregel is niet constant.** Bij rugnummer 217 staat
  `217.<del ...> Henri-François Haquin</del>`: geen spatie ná de punt maar
  erbinnen, als enige van de 184. Met `\s` in plaats van `\s*` viel die
  renner weg en telde Team Picnic PostNL zeven man — geen fout, geen leeg
  veld, gewoon een renner minder.

### Het adres is opnieuw niet af te leiden

`spain-riders-2026` bij de Vuelta, `riders-rt-2026` bij de Renewi Tour,
`riders-gb-2026` bij de Tour of Britain. Dezelfde onraadbare afkorting als
bij de routepagina's, dus dezelfde oplossing: `startlijst_kandidaten` leest
de link van de koerspagina.

Met één verschil dat anders stil misgaat: **de startlijst hangt onder een
ándere map dan de routepagina.** De kalender wijst voor de Vuelta naar
`/vuelta-2026-route/spain-route-2026/`, de startlijst staat op
`/vuelta-2026/spain-riders-2026/`. Filteren op de map van de meegegeven URL —
wat `route_kandidaten` doet — zou hem nooit vinden. Daarom wordt `-route` er
ook afgehaald; van de 49 koersen van 2026 hebben alleen de Giro, de Tour en
de Vuelta een koersmap die daarop eindigt.

Het kost twee verzoeken per koers per dag (`_startlist_cache`): één om het
adres te vinden, één voor de pagina zelf. Ook een lege uitkomst blijft in de
cache, anders wordt een koers waarvan de startlijst nog niet gepubliceerd is
elke ronde opnieuw geprobeerd.

### Wat het kost, gemeten

`python3 tools/meet_attributen.py` leest de echte fixture:

| selectie | rijen | bytes |
|---|---:|---:|
| 1 renner per ploeg (standaard) | 23 | 1 691 |
| 2 per ploeg | 46 | 3 398 |
| 3 per ploeg | 69 | 5 095 |
| de hele lijst | 184 | 13 720 |
| alleen de tellingen | — | 64 |

Netto op een koers zonder uitslag: +1 711 bytes met de standaard. Dat is
geen reden om het niet te doen — de attributen zitten toch al ruim boven de
grens van de recorder — maar de hele lijst meesturen zou de zwaarste post
van de sensor evenaren en dat is hij niet waard.

### Wat hiervan niet geverifieerd is

- **Of andere koersen dezelfde opmaak hebben.** Er is één fixture: de
  Vuelta, mannen, grote ronde. Over een eendaagse koers, een vrouwenkoers of
  een pagina die nog niet gevuld is zegt die niets, en de proxy laat
  cyclingstage niet door.
- **Of het adres altijd via de koerspagina te vinden is.** Voor drie koersen
  is dat nagekeken in de opgeslagen HTML (Vuelta, Renewi Tour, Tour of
  Britain); voor de andere 46 niet.
- **Wat de `datetime` bij een doorgestreepte renner betekent.** Negen
  renners bij acht verschillende ploegen dragen exact dezelfde tijdstempel
  tot op de seconde, en alle stempels liggen ná de eerste koersweek terwijl
  de koers eerder begon. Dat is dus géén uitvalmoment — vermoedelijk een
  publicatiemoment. Daarom wordt alleen de vlag (`out`) gebruikt en de datum
  niet: hij zou een precisie suggereren die er niet is.

Werkt de startlijst niet, zoek dan in het debuglogboek op "Startlijst".

## Opzetten: de entiteit wacht niet op een geslaagde ronde

`async_setup_entry` in `sensor.py` gebruikt bewust `async_refresh()` en
**niet** `async_config_entry_first_refresh()`. Die laatste gooit
`ConfigEntryNotReady` zodra de eerste ophaalronde faalt, en dan wordt de
entiteit niet toegevoegd. Home Assistant zet er dan zelf een neer uit het
entiteitsregister: status `unavailable`, attribuut `restored: true`, verder
niets. Daar is niet aan te zien dát het opzetten mislukte en al helemaal
niet waarom — en de kaart tekende er een lege tegel mee ("1 km · Profiel nog
niet bekend"). **`restored: true` op deze sensor betekent dus: de integratie
is niet geladen, kijk in het log, niet naar de data.**

Eén mislukte ronde bij procyclingstats hoort deze integratie ook niet te
blokkeren: er hangt geen apparaat aan en de bron ligt er weleens even uit.
De prijs is dat Home Assistant de entry als geladen beschouwt en zelf niet
opnieuw probeert; dat doet de coordinator al op zijn eigen ritme. Mislukt de
eerste ronde, dan logt `async_setup_entry` een waarschuwing met de reden.

Om dezelfde reden staat `_registreer_kaart` in `__init__.py` in een `try`:
zijn eigen fouten ving het al af, maar `add_extra_js_url` en het lezen van
het kaartbestand niet, en een dashboardkaart hoort de sensor nooit onderuit
te halen.

## Diagnose-attributen

Deze zitten er puur om problemen op te sporen en mogen weg zodra het stabiel is:
`gpx_diag`, `gpx_used`, `times_diag`, `names_diag`, `levels_diag`,
`elevation_source`.

## Dashboard

De kaart hoort bij de integratie: `www/cycling-next-race-card.js` wordt in
`__init__.py` geserveerd via `async_register_static_paths` en aangemeld met
`add_extra_js_url`. Daarvoor staan `frontend` en `http` in de manifest onder
`dependencies`. De gebruiker voegt alleen
`type: custom:cycling-next-race-card` toe; geen resources, geen templates,
geen button-card of Bubble Card.

Achter de URL hangt `?v={VERSION}-{hash}`, waarbij de hash uit de inhoud van
het kaartbestand komt (`_bestandsstempel`). Dat is bewust niet alleen
`VERSION`: die werd drie kaartwijzigingen lang vergeten op te hogen, waardoor
browsers een oude kaart bleven tonen. `VERSION` in `const.py` moet nog steeds
gelijk zijn aan `version` in de manifest; `tests/test_kaart.py` bewaakt beide.

De kaart draagt datzelfde nummer nog een keer, als `VERSIE` bovenin het
bestand: hij is statisch en weet niets van `const.py`. Dat nummer staat in
de console én onder in het bewerkscherm van de kaart, en is de enige manier
om te zien wélke kaart een browser draait — Home Assistant meldt bij de
integratie de Python-kant, ook als de frontend nog een oude kaart uit de
cache haalt. Op een telefoon is er geen console, dus die regel in het
bewerkscherm is daar het enige aanknopingspunt. Ook dit nummer wordt door
`tests/test_kaart.py` vergeleken.

De kaart gaat bij voorkeur in de **resourcelijst van Lovelace**
(`_als_lovelace_resource`), niet via `add_extra_js_url`. Lovelace laadt zijn
resources en wacht daarop vóór het tekenen van de kaarten; bij extra_js_url
gebeurt dat niet en verscheen er soms een foutkaart die na verversen weg
was. Dat lukt alleen in storage-modus — in YAML-modus beheert de gebruiker
de lijst zelf — en dan valt het terug op `add_extra_js_url`, met een
waarschuwing in het log zodat je kunt zien dat het die weg is geworden.
`lovelace` staat in de manifest onder `after_dependencies`, zodat het er is
wanneer wij opzetten.

**De modus van Lovelace is niet aan een veldnaam af te lezen.** Tot en met
0.9.1 keek `_als_lovelace_resource` naar `lovelace.resource_mode` en dat gaf
op élke versie waarop de integratie ooit draaide `None`:
`hass.data["lovelace"]` is t/m HA 2024.12 een **dict**, van 2025.2 t/m
2026.1 een dataclass met `mode`, en pas vanaf 2026.2 een dataclass met
`resource_mode` (daar is `mode` hernoemd, omdat de modus van de resources
losstaat van die van de dashboards). De registratie viel dus
altijd stil terug op extra_js_url — precies de weg die de foutkaart
oplevert waar gebruikers over klaagden, terwijl het commentaar in de code
beweerde dat dat opgelost was. `_resourcecollectie` leest daarom beide
vormen en vraagt de modus aan de collectie zélf: alleen
`ResourceStorageCollection` heeft `async_create_item`/`async_update_item`,
`ResourceYAMLCollection` kent enkel `async_get_info` en `async_items`. Die
capability-controle overleeft een volgende hernoeming; `tests/test_kaart.py`
heeft een test per vorm.

Omdat het script daardoor langs twee wegen kan binnenkomen, staat elke
`customElements.define` achter een `customElements.get`-controle: twee keer
definiëren gooit een DOMException en breekt alles alsnog.

De kaart kent twee weergaven: `view: profile` tekent het hoogteprofiel,
`view: countdown` een compacte regel met koers, datum en `countdown` uit de
sensor. `visible_days` bepaalt vanaf hoeveel dagen voor de koers de kaart
verschijnt; `0` betekent altijd, en dat is de standaard bij `countdown`
(die weergave is juist bedoeld om er buiten koersen om te blijven staan).
De verouderde `always_show: true` wordt nog geaccepteerd als `visible_days: 0`.

`design` kiest de vormgeving: `default` (de eigen opmaak), `ha` (volgt de
variabelen van het actieve HA-thema, accent `--primary-color`) of `bubble`
(nagebootste Bubble Card-stijl — die kaart is er niet voor nodig en wordt
ook niet gebruikt). Het zit in één `STIJL`-blok: `_teken` zet
`thema-<design>` op `ha-card` én op `dialog`, de rest is CSS. Bewust geen
tweede stijlvariabele, want `tests/test_browsercompat.py` scant `STIJL` en
`EDITOR_STIJL` op te nieuwe CSS en zou een derde blok missen. Let daarbij
op de gap-controle: elke selector met `display:flex` moet een eigen
`> * + *`-marge hebben, dus voeg in een thema liever geen nieuwe
flex-container toe.

De hoogteprofielen volgen het thema **niet**: die tekencode is gedeeld met
de button-card-templates en moet daar letterlijk gelijk aan blijven.

`levels` bepaalt welke niveaus déze kaart laat zien, met dezelfde tabel als
`NIVEAUS` in `const.py` — die staat nog een keer in de kaart, want die is
statisch; `tests/test_kaart.py` vergelijkt de twee. Het is een keuze uit wat
de sensor levert en géén tweede knop om koersen op te halen. Daarvoor draagt
elk blok in `races` en elke etappe in `upcoming` een `level`, en elk blok
bovendien `days_until`.

Blijft er na het filteren geen koers over, dan verbergt de kaart zich (zoals
bij `visible_days`); in de voorvertoning blijft hij staan met een melding,
anders is hij in het bewerkscherm niet meer terug te vinden.

**Een sensor op `unavailable` of `unknown` krijgt een eigen melding.** Zonder
die controle tekende de kaart gewoon de tegel met lege attributen, en omdat
`svgTegel` bij een ontbrekende afstand op `1` terugvalt (`Number(a.distance_km)
||1`) stond er "1 km · Profiel nog niet bekend" — niet te onderscheiden van
een koers waarvan alleen het profiel ontbreekt, terwijl er in werkelijkheid
niets was opgehaald. Verbergen is hier verkeerd: dan is er niets meer om aan
te zien dat er iets mis is.

Valt de koers van de sensor weg, dan schuift de kaart de eerste koers die
wél mag naar de tegel (`tegelAttributen`): koersgegevens uit het blok in
`races`, het etappeprofiel uit `upcoming` — precies zoals de pop-up dat al
deed. Wat de sensor alleen voor zijn eigen koers levert (de live-positie,
`countdown`, `date`, `type`) ontbreekt dan gewoon; niets bijverzinnen.

Let op de verouderde `other_*`-uitslag in `koersblok`: die hoort bij een
koers die de sénsor uitkoos en kan dus van een uitgezet niveau zijn. De
voorwaarde telt daarom de koersen vóór het filteren (`koersen(a).length < 2`),
niet erna — op `meerdere` afgaan liet zo'n koers alsnog binnen zodra het
filter er één overhield.

Een onderdeel erbij raakt twee plekken: `SECTIES` in de kaart en de opsomming onder "Onderdelen van het detailvenster" in de README; `tests/test_kaart.py` faalt als er één achterblijft.

`sections` bepaalt welke onderdelen in het detailvenster staan (`SECTIES`);
de volgorde ligt in de code vast en niet in de configuratie. Leeg of onzin
betekent alles, zodat een kaart zonder die optie blijft tonen wat hij altijd
toonde — ook een onderdeel dat er later bij komt. Daarom staat `sections`
niet in `getStubConfig`, en haalt `_wijzig` hem er weer uit zodra alles is
aangevinkt (net als een lege `title`); anders zou elke kaart die vandaag
wordt aangemaakt een toekomstig onderdeel stilzwijgend missen. Staat
`profile` uit, dan schuift de eerste etappe van een pop-upkoers door naar
"Komende dagen": die werd anders nergens meer getekend.

De kaart heeft een visuele editor (`cycling-next-race-card-editor`) achter
`getConfigElement()`. Die gebruikt `ha-form` als dat element bestaat en valt
anders terug op een eigen formulier. Wie een kaartoptie toevoegt raakt vier
plekken: `setConfig`, de lijst `VELDEN` in de editor, het terugvalformulier
en de optietabel in de README; `tests/test_kaart.py` faalt als er één
achterblijft, `tests/browser/editor_test.mjs` vergelijkt beide editorwegen.
Vergeet daarbij de `setConfig` van de editor niet: die staat er los van die
van de kaart en moet dezelfde standaardwaarden en normalisering hebben.
Schrijf sleutels in `this._config` voluit (`view: view`, niet de verkorte
vorm), want die test leest ze met een regex. De optietabel in de README
loopt tot de eerste regel die geen tabelrij is; tabellen met de wáárden van
een optie horen daaronder.

**`ha-form` houdt zijn eigen data bij.** Het formulier één keer opbouwen en
daarna alleen `this._config` bijwerken is niet genoeg: `ha-form` doet
`this.data = {...this.data, ...nieuw}` en stuurt bij een wijziging zijn
eigen data terug. Home Assistant roept `setConfig` op hetzelfde
editor-element opnieuw aan zodra de configuratie buiten het formulier om
verandert — `hui-element-editor._setConfig()` doet dat onder meer na elke
wijziging in de code-editor achter *Toon code-editor*, en het element wordt
alleen weggegooid als het kaarttype verandert. Zonder `this._form.data =
this._config` in `_teken` bleef het formulier op de oude waarden staan en
sloeg de eerstvolgende wijziging die oude waarden weer op. Met `sections`
en `title`, die `_wijzig` juist weglaat als ze niets toevoegen, betekende
dat: sleutels stilzwijgend kwijt.

`setConfig` mag nooit een uitzondering gooien — Home Assistant maakt daar
een foutkaart van, en die is voor de gebruiker niet te repareren. Wat er
binnenkomt wordt daarom genormaliseerd (`vormgeving()`, `secties()`) in
plaats van afgekeurd. Datzelfde geldt voor `set hass` vóór `setConfig`: dat
komt voor en moet stilletjes niets doen. En `setConfig` tekent zelf opnieuw
als `hass` er al is; zonder dat bleef het bewerkscherm de oude vormgeving
tonen, want daar komt geen nieuwe status voorbij.

**De tekencode staat op twee plekken.** De drie SVG-functies (`svgTegel`,
`svgDetail`, `svgKomend`) zijn letterlijk overgenomen uit de
button-card-templates in `lovelace/`, die er nog staan voor de oude opzet.
`tests/test_kaart.py` vergelijkt ze regel voor regel per functie — zoeken in
het hele bestand werkt niet, want dezelfde regels komen in meerdere functies
voor. Wijzig je de een, wijzig dan de ander.

Registratie faalt zacht: lukt het serveren niet, dan logt het een
waarschuwing en draait de sensor gewoon door.

**De kaart moet op oude WebViews draaien.** `add_extra_js_url` zet het
script op **elke** frontend-pagina, ook op de loginpagina en op dashboards
zonder onze kaart. Eén stuk te nieuwe syntax is een SyntaxError bij het
parsen en legt daarmee de hele frontend van dat apparaat plat; de gebruiker
kan er alleen omheen door de integratie uit te zetten. Wandpanelen (Sonoff
en dergelijke) draaien vaak de WebView van Android 8, oftewel Chrome 60/61.

Vandaar de ondergrens ES2018 / Chrome 61. Niet gebruiken: `?.` en `??`
(Chrome 80, SyntaxError), `replaceChildren` (86), `gap` in flexbox (84,
wordt stil genegeerd waardoor de opmaak in elkaar valt), `inset`, `:is()`,
`:where()`, `clamp()`. `tests/test_browsercompat.py` scant daarop en
`tests/browser/syntax_test.mjs` parseert het bestand met acorn als ES2018.

Let op: `esbuild --target=chrome61` is hiervoor géén controle — dat
transpileert de syntax weg en meldt niets. Een parser die weigert is wat je
wilt.

De browsertests draaien op een moderne Chromium en zouden dit dus nooit
vangen; die controleren of het beeld klopt, niet of het ergens laadt.

`tests/test_dashboard.py` controleert dat elk attribuut dat een kaart
opvraagt ook echt door `sensor.py` wordt gezet, dat gebruikte templates
bestaan, en dat tegel en pop-up dezelfde hash delen.

SVG-conventies: `viewBox` breedte 440, kleuren via `currentColor` zodat het
thema volgt, categoriekleuren `CAT={HC:'#E4572E','1':'#F2A03D','2':'#EBD24A',
'3':'#7FB069','4':'#5FA8A0'}`, accent `#E4572E`.

In de uitslag en de klassementen staat de ploeg achter de renner
(`rennerMetPloeg`): de officiële ploegcode als die bekend is (`team_code`),
anders de volledige naam. Naam en ploeg zitten in hetzelfde vakje (`.naam`
met ellipsis, `.ploeg` gedimd erbinnen), zodat bij weinig ruimte eerst de
ploeg wegvalt en de rennernaam heel blijft; nagekeken op 360 px.

### Ploegcodes zijn er niet meer

Tot 0.24 stond de officiële UCI-ploegcode achter elke renner; die kwam van
de ploegpagina bij procyclingstats en is met die bron verdwenen. Cyclingstage
geeft in de uitslag alleen een landcode, en op de startlijst de volledige
ploegnaam. `rennerMetPloeg` in de kaart valt daar in die volgorde op terug:
`team_code` als hij er is, anders `team`, anders het land.

Zelf een code uit de naam afleiden zou iets opleveren dat op een
UCI-ploegcode lijkt zonder het te zijn — precies wat "nooit data verzinnen"
verbiedt.

## Uitbrengen

HACS toont de naam van een GitHub-release; zonder releases valt het terug op
de laatste commit en staat er een hash in de updatekaart. `.github/workflows/
release.yml` maakt de release zodra een tag `vX.Y.Z` wordt gepusht, en weigert
als die tag niet overeenkomt met `version` in de manifest.

Het versienummer staat op drie plekken: `version` in `manifest.json`,
`VERSION` in `const.py` en `VERSIE` bovenin de kaart.
`tests/test_kaart.py` bewaakt dat ze gelijk zijn.
Ophogen doe je in de commit met de wijziging zelf (zie "Werkafspraken"), niet
pas hier; taggen is dan alleen nog het nummer dat er al staat vastleggen.

Uitbrengen is dus: zet de wijziging mét ophoging op `main` en tag daarna
`vX.Y.Z` met datzelfde nummer. Dat hoort in dezelfde beurt als de wijziging
zelf (zie "Werkafspraken"); wachten op toestemming is niet nodig en heeft al
één keer een versie laten stilstaan. De workflow weigert een tag die niet
overeenkomt met de manifest — anders installeert HACS `v0.5.0` terwijl Home
Assistant `0.4.0` rapporteert.

Niet elke ophoging wordt uitgebracht: `v0.6.0` heeft in de manifest gestaan
maar heeft nooit een tag gekregen. Zoek zo'n versie terug via het
commitbericht (`git log --oneline --grep '^v0\.6\.0'`) of, voor commits van
vóór die afspraak, via `git log -L 14,14:custom_components/cycling_next_race/const.py`.

## Openstaande punten

**Wat er aan opgeslagen pagina's nodig is staat in
`docs/gevraagde-paginas.md`**, op volgorde van wat het meest oplevert. Vul die
lijst aan zodra er een nieuwe blinde vlek bij komt, en streep af wat er als
fixture in `tests/fixtures/` is geland.

- **Live: geen bron aangesloten, wel in kaart gebracht.** Zie "Live: welke
  bron" hierboven. ASO Race Center is de meest lonende eerste stap; de
  live-feed zelf is nog niet vastgesteld en de `robots.txt` van ASO is nog
  niet nagekeken.
- Categorieën van cols ontbreken vaak vóór de koers (PCS publiceert ze pas na
  afloop via het bergklassement). Uitzoeken of het elders vooraf beschikbaar is.
- Een aantal cyclingstage-namen voor vrouwenklassiekers is een educated guess
  (`CYCLINGSTAGE_ONEDAY`); daarom staan er meerdere kandidaten per koers.
- De config flow is niet in een draaiende Home Assistant beproefd: de tests
  bouwen het optieschema op met gestubde HA-modules, wat niets zegt over de
  vraag of het scherm verschijnt en de entry laadt.
- Overweeg de diagnose-attributen te verwijderen zodra alles stabiel draait.
- **De ProSeries-circuitnummers (26 en 27) zijn niet geverifieerd.** Kijk ze
  na zodra er een omgeving is die bij procyclingstats kan: open
  `races.php?year=<jaar>&circuit=26&class=&filter=Filter` en kijk of daar de
  ProSeries-kalender staat. `levels_diag` op de sensor laat intussen zien of
  een niveau koersen oplevert. Klopt een nummer niet, pas dan `NIVEAUS` in
  `const.py` aan — verder verandert er niets.
- Meer niveaus toevoegen (Europe Tour, nationale kampioenschappen) kan met
  een regel in `NIVEAUS`, maar alleen met een nummer dat is nagekeken. Europe
  Tour is bewust weggelaten: die lijst is enorm en het nummer is onzeker.
- `LEIDERSTRUI` dekt alleen de koersen waarvan de truikleur vaststaat. Voor
  de rest (Catalunya, Baskenland, Denemarken, Renewi, Groot-Brittannië …)
  is er bewust niets ingevuld. Aanvullen mag, maar alleen na controle.
- **De cyclingstage-adressen van de etappeteksten zijn per koers gecheckt via
  zoekresultaten, niet door de pagina te openen.** Voor Giro en Vuelta stond
  er de koersnaam waar het land hoort (`stage-5-giro-2026` in plaats van
  `stage-5-italy-2026`); de Tour klopte wel. De overige koersen in
  `CYCLINGSTAGE_ROUTE` zijn niet opnieuw nagelopen.
