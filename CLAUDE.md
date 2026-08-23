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
  `_prevrank_cache`, `_startlist_cache` (de startlijst per koers),
  `_gpxindex_cache` (de GPX-adressen die cyclingstage zelf op een rij zet,
  per koers; alleen gevuld als de vaste adressen falen),
  `_ranking_cache` (de PCS-ranglijst per adres uit `RANGLIJST`),
  `_other_cache` (dict
  per etappe van de andere koersen; alleen afgeronde etappes komen erin).
  `_tv_cache` bewaart de tv-gids als HTML — op die pagina staan álle koersen
  van de dag, dus één verzoek bedient de tegel en de pop-up samen.
  `_sprints_cache` en `_prevrank_cache` zijn dicts per etappe en geen enkele
  plek, want de koersen in de pop-up vragen ze ook op.
  `_elev_cache` heeft `(etappe, aantal punten)` als sleutel: dezelfde etappe
  wordt als komende dag met 60 punten opgehaald en als getoonde etappe met
  200. Stond alleen de URL in de sleutel, dan kreeg het grote profiel de
  kleine versie terug. `_gpx_beschikbaar` houdt los bij of een etappe een
  profiel heeft, want `_gpx_rang` heeft dat nodig om te kiezen wélke koers
  getoond wordt.

### Welke niveaus meedoen

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

- `last_result`, `gc_top`, `points_top`, `kom_top`, `youth_top` — met
  dagwinst, op dezelfde manier berekend als op de tegel: de stand van de
  vorige etappe via `_rank_maps` en koppelen op **positie** (kolom "Prev"),
  nooit op naam.
- `channels` en `channels_detail` — waar die koers te zien is, uit dezelfde
  tv-gids. `_zenders_voor` slaat een koers over die verder dan zes dagen weg
  is, want zo ver kijkt de gids niet vooruit.
- Het profiel komt uit `upcoming` (zie hieronder), inclusief `start_time`,
  `finish_est` en de tussensprint.

### Startlijst als er nog geen uitslag is

Een koers die nog moet beginnen heeft niets te tonen: geen uitslag, geen
klassement. Daar komt de startlijst voor in de plaats — `startlist_top`,
`startlist_riders` en `startlist_teams`, op de tegel én op elk koersblok, en
alleen zolang `last_result` leeg is. Zodra er gereden is verdwijnt hij weer;
dat scheelt ruimte in de attributen en de uitslag zegt meer.

De startlijst zelf staat op volgorde van ploeg en zegt niets over wie de
kopmannen zijn. **De volgorde komt daarom van de individuele PCS-ranglijst**
(`RANGLIJST`, per geslacht één adres, één keer per dag opgehaald), gekoppeld
op `rider_url` — een vaste sleutel, dus zonder namen te vergelijken. Wie niet
op die ranglijst staat komt niet in het lijstje: een renner een geschatte
plek geven zou precies het verzinnen zijn dat dit project niet doet. `rank`
in de rijen is dan ook de plek op die ranglijst en geen 1-2-3 van onszelf;
de kaart zet dat er met zoveel woorden bij.

Levert de ranglijst niets op (of klopt het vrouwenadres niet), dan blijft
`startlist_top` leeg en laat de kaart het lijstje weg; de telling van renners
en ploegen blijft dan wel staan. `_fetch_ranking` logt een waarschuwing en
`startlist_diag` laat zien hoeveel renners er gekoppeld konden worden.

`_zenders_voor`, `_sprints_voor` en `_rank_maps` slikken hun eigen fouten en
geven leeg terug. Dat moet: `_races_block` vangt een uitzondering per blok af
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

### procyclingstats (pakket `procyclingstats==0.2.8` + `cloudscraper` + `curl_cffi`)

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
  voor de vrouwen `rankings/we/individual`. Zie `RANGLIJST` in `sensor.py`;
  het vrouwenadres is **niet geverifieerd**.

### cyclingstage.com

| Doel | Patroon |
|---|---|
| GPX grote rondes | `cdn.../images/{slug}/{y}/stage-{n}-parcours.gpx` |
| GPX overige + vrouwen | `cdn.../images/{slug}/{y}/stage-{n}-route.gpx` |
| GPX eendaags | `cdn.../images/{slug}/{y}/route.gpx` |
| GPX-overzicht per koers | `www.../{slug}-{y}-gpx/` |
| Tijdschema (tussensprint) | `www.../images/{slug}/{y}/stage-{n}-times.htm` |
| Etappetekst (colnamen, finishtijd) | per koers een sjabloon, zie `CYCLINGSTAGE_ROUTE` |

**Die GPX-adressen zijn een aanname over de bestandsnaam, geen bron.** Wijkt
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
koers de zenders en tijden. De parser (`_parse_channels`) zet vlag-afbeeldingen
en koerslinks om in tekstmarkers en splitst daarop. Toont ~6 dagen vooruit,
dus alleen ophalen bij `days_until <= 6`.

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
daarbij een waarschuwing; de volledige state gaat bovendien bij elke update
over de websocket naar élke verbonden client. De hoogteprofielen wegen het
zwaarst: `elevation` van de getoonde etappe (200 punten) plus een profiel per
komende etappe. Die laatste stonden op 150 punten, wat de state op ruim 34 kB
bracht; met 60 punten is dat 24 kB en visueel niet te onderscheiden — de
profieltjes in "Komende dagen" zijn maar een paar pixels hoog.

Onder de 16 kB komt alleen door `upcoming` verder in te perken: minder
etappes, of de profieltjes eruit. Beide kosten iets zichtbaars, dus dat is
een keuze en geen vanzelfsprekendheid.

`races` komt daar bovenop: een koersblok is ruwweg 4 kB (uitslag, algemeen,
punten, berg, jongeren; de zenders erbij zijn een paar honderd bytes) en er
passen er `max_other` naast de getoonde. In de
praktijk is dat er één — mannen en vrouwen — dus zo'n 28 kB. Bewust géén
hoogteprofiel in het blok; dat komt uit `upcoming` via `race_key`, anders was
het een stuk meer. Wordt het te veel, dan is `max_other` verlagen de
goedkoopste stap; dat is nu een instelling en hoeft niet meer in de code.
**De schatting klopt: het gaat er in de praktijk overheen.** Het log van
21-22 augustus 2026 staat vol met `State attributes for
sensor.cycling_next_race exceed maximum size of 16384 bytes ... Attributes
will not be stored` — bij elke update. De sensor werkt gewoon (de
attributen gaan wel over de websocket naar de kaart), maar de recorder
bewaart ze niet, dus er is geen historie van. Wie dat wil oplossen zal
`upcoming` of `max_other` moeten inperken; beide kosten iets zichtbaars.

De startlijst komt er niet bovenop maar staat in de plaats van de uitslag:
tien renners is zo'n 600 bytes per koers, en een koers zonder uitslag heeft
juist geen `last_result`, `gc_top` en de rest. Per saldo scheelt het.

`level` op elke etappe in `upcoming` en op elk blok in `races` kost een stuk
of vijftien bytes per stuk — een paar honderd in totaal, en het alternatief
(de kaart laten raden welk niveau een koers heeft) bestaat niet.

Een niveau erbij kost niets zolang er niet méér koersen in beeld komen:
`max_other` begrenst het aantal blokken en `upcoming_n` het aantal etappes.
Wat het wél kost zijn verzoeken bij procyclingstats — een kalenderpagina per
niveau per dag, en een etappelijst per koers die in het venster valt.

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
`gpx_diag`, `gpx_used`, `times_diag`, `names_diag`, `levels_diag`, `startlist_diag`,
`gain_headers`, `gain_raw`,
`names_fixed`, `gains_set`, `roster_size`, `elevation_source`.

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

### Ploegcodes

De code komt van de **ploegpagina bij procyclingstats**
(`_fetch_team_abbr` → `Team(team_url).abbreviation()`), niet uit de naam.
Zelf initialen maken zou iets opleveren dat op een UCI-ploegcode lijkt
zonder het te zijn; dat is precies wat "nooit data verzinnen" verbiedt.
Vandaar ook de controle `^[A-Z0-9]{2,4}$`: geeft de pagina de volledige naam
of iets anders terug, dan telt het niet als code en blijft de naam staan.

Het adres van de ploegpagina komt uit de tabellen zelf: `_fetch_stage`
vraagt `team_url` mee (met terugval op de oude veldenlijst als de pagina hem
niet geeft) en zet `data["team_urls"]` als `{ploegnaam: adres}`. Dat blijft
binnen de coordinator — in de rijen zou het alleen ruimte in de attributen
kosten. De rijen krijgen alleen `team_code`, drie tekens.

`_ploegcodes` haalt per ronde hoogstens `MAX_PLOEGCODES_PER_RONDE` (12)
nieuwe codes op: een koers telt zo'n twintig ploegen en elke code is een
eigen pagina, dus alles ineens maakt de eerste update na een herstart
onnodig lang. Wat nog niet bekend is houdt zolang de volledige naam en volgt
de ronde erna. `_abbr_cache` staat op ploegnaam en gaat een dag mee; een
mislukte poging staat als `""` in de cache, zodat hij niet elke ronde
opnieuw wordt geprobeerd maar morgen wel.

Aanroepen gebeurt **na** `_repair_rows`: dat vergelijkt de ploegkolom met de
startlijst, en die noemt de volledige naam. Ook op een uitslag uit
`_other_cache`, anders krijgen de rijen die vorige ronde buiten de twaalf
vielen nooit meer een code.

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
`vX.Y.Z` met datzelfde nummer. De workflow weigert een tag die niet
overeenkomt met de manifest — anders installeert HACS `v0.5.0` terwijl Home
Assistant `0.4.0` rapporteert.

Niet elke ophoging wordt uitgebracht: `v0.6.0` heeft in de manifest gestaan
maar heeft nooit een tag gekregen. Zoek zo'n versie terug via het
commitbericht (`git log --oneline --grep '^v0\.6\.0'`) of, voor commits van
vóór die afspraak, via `git log -L 14,14:custom_components/cycling_next_race/const.py`.

## Openstaande punten

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
- **Het vrouwenadres van de ranglijst (`rankings/we/individual`) is niet
  geverifieerd.** Net als bij de ProSeries-nummers kon dat van hieruit niet
  worden nagekeken. Klopt het niet, dan blijft de startlijst van een
  vrouwenkoers leeg; kijk in het debuglogboek op "Ranglijst" en op
  `startlist_diag`. Aanpassen is één regel in `RANGLIJST` in `sensor.py`.
- **`Ranking.individual_ranking()` is niet geverifieerd** met de velden
  `rank`, `rider_url` en `points`; ze staan zo in de documentatie van het
  pakket, maar de sandbox komt niet bij procyclingstats. Faalt het, dan is
  de startlijst leeg — niet de hele sensor.
- **De GPX-overzichtspagina is niet in het echt gelezen.** Dat de pagina
  bestaat en `{slug}-{jaar}-gpx` heet, is nagekeken via zoekresultaten met
  echte adressen (`vuelta-2026-gpx`, `giro-2026-gpx`,
  `tour-de-france-2026-gpx`); hoe de links erop staan is dat **niet** — de
  proxy laat cyclingstage niet door. `_parse_gpx_index` is daarom zo ruim
  mogelijk gehouden (elke `href` die op `.gpx` eindigt, nummer uit het
  bestandspad) en de test ernaast draait op synthetische HTML. Werkt de
  terugval niet, kijk dan in het debuglogboek op "GPX-overzicht": daar staat
  of de pagina binnenkwam en hoeveel links eruit kwamen.
- **De cyclingstage-adressen van de etappeteksten zijn per koers gecheckt via
  zoekresultaten, niet door de pagina te openen.** Voor Giro en Vuelta stond
  er de koersnaam waar het land hoort (`stage-5-giro-2026` in plaats van
  `stage-5-italy-2026`); de Tour klopte wel. De overige koersen in
  `CYCLINGSTAGE_ROUTE` zijn niet opnieuw nagelopen.
- **`Team.abbreviation()` is niet geverifieerd.** Of het pakket die methode
  zo noemt in 0.2.8, en of `team_url` als veld in de uitslagtabellen wordt
  geaccepteerd, blijkt pas in een draaiende Home Assistant — de sandbox komt
  niet bij procyclingstats. Beide staan achter een terugval: geen `team_url`
  betekent de oude veldenlijst, en geen bruikbare code betekent de volledige
  ploegnaam. Blijft de code overal weg, zoek dan in het debuglogboek op
  "Ploegcode"; daar staat wat de pagina wél teruggaf.
