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
  `_prevrank_cache`, `_roster_cache` (dict per koers), `_other_cache` (dict
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
2. koers mét hoogteprofiel (`_gpx_rang`)
3. bij gelijke stand de mannen

en pas daarna nog gefilterd op `_mag_op_tegel`.

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

### procyclingstats (pakket `procyclingstats==0.2.8`)

- Kalender: `races.php?year={y}&circuit={c}&class=&filter=Filter`
  - `circuit=1` mannen-WorldTour, `circuit=24` Women's WorldTour (geverifieerd)
  - Kalenderlinks eindigen soms op `/gc` of `/result` → normaliseren naar
    `race/<slug>/<jaar>` met een regex, anders breekt de etappelijst.
- Etappe: `Stage(stage_url)`; bij een **eendaagse** koers staat de info op
  `{url}/result` (zie `_stage_obj`).
- Cols vooraf: `RaceClimbs(f"{stage_url}/route/climbs")` — voorspelbaar adres,
  werkt voor élke koers. Dit is de terugval voor colnamen.
- Startlijst: `RaceStartlist(f"{race_url}/startlist")` — per ploegblok geparsed,
  dus de koppeling renner→ploeg is hier betrouwbaar.

### cyclingstage.com

| Doel | Patroon |
|---|---|
| GPX grote rondes | `cdn.../images/{slug}/{y}/stage-{n}-parcours.gpx` |
| GPX overige + vrouwen | `cdn.../images/{slug}/{y}/stage-{n}-route.gpx` |
| GPX eendaags | `cdn.../images/{slug}/{y}/route.gpx` |
| Tijdschema (tussensprint) | `www.../images/{slug}/{y}/stage-{n}-times.htm` |
| Etappetekst (colnamen, finishtijd) | per koers een sjabloon, zie `CYCLINGSTAGE_ROUTE` |

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
**Niet gemeten in een draaiende Home Assistant, alleen geschat.**

Een niveau erbij kost niets zolang er niet méér koersen in beeld komen:
`max_other` begrenst het aantal blokken en `upcoming_n` het aantal etappes.
Wat het wél kost zijn verzoeken bij procyclingstats — een kalenderpagina per
niveau per dag, en een etappelijst per koers die in het venster valt.

## Diagnose-attributen

Deze zitten er puur om problemen op te sporen en mogen weg zodra het stabiel is:
`gpx_diag`, `times_diag`, `names_diag`, `levels_diag`, `gain_headers`, `gain_raw`,
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

De kaart gaat bij voorkeur in de **resourcelijst van Lovelace**
(`_als_lovelace_resource`), niet via `add_extra_js_url`. Lovelace laadt zijn
resources en wacht daarop vóór het tekenen van de kaarten; bij extra_js_url
gebeurt dat niet en verscheen er soms een foutkaart die na verversen weg
was. Dat lukt alleen in storage-modus — in YAML-modus beheert de gebruiker
de lijst zelf — en dan valt het terug op `add_extra_js_url`. `lovelace`
staat in de manifest onder `after_dependencies`, zodat het er is wanneer wij
opzetten.

Omdat het script daardoor langs twee wegen kan binnenkomen, staat elke
`customElements.define` achter een `customElements.get`-controle: twee keer
definiëren gooit een DOMException en breekt alles alsnog.

De kaart kent twee weergaven: `view: profile` tekent het hoogteprofiel,
`view: countdown` een compacte regel met koers, datum en `countdown` uit de
sensor. `visible_days` bepaalt vanaf hoeveel dagen voor de koers de kaart
verschijnt; `0` betekent altijd, en dat is de standaard bij `countdown`
(die weergave is juist bedoeld om er buiten koersen om te blijven staan).
De verouderde `always_show: true` wordt nog geaccepteerd als `visible_days: 0`.

De kaart heeft een visuele editor (`cycling-next-race-card-editor`) achter
`getConfigElement()`. Die gebruikt `ha-form` als dat element bestaat en valt
anders terug op een eigen formulier. Wie een kaartoptie toevoegt raakt drie
plekken: `setConfig`, de lijst `VELDEN` in de editor, en de optietabel in de
README; `tests/test_kaart.py` faalt als er één achterblijft. Schrijf sleutels
in `this._config` voluit (`view: view`, niet de verkorte vorm), want die test
leest ze met een regex.

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

Het versienummer staat op twee plekken: `version` in `manifest.json` en
`VERSION` in `const.py`. `tests/test_kaart.py` bewaakt dat ze gelijk zijn.
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
- **`Team.abbreviation()` is niet geverifieerd.** Of het pakket die methode
  zo noemt in 0.2.8, en of `team_url` als veld in de uitslagtabellen wordt
  geaccepteerd, blijkt pas in een draaiende Home Assistant — de sandbox komt
  niet bij procyclingstats. Beide staan achter een terugval: geen `team_url`
  betekent de oude veldenlijst, en geen bruikbare code betekent de volledige
  ploegnaam. Blijft de code overal weg, zoek dan in het debuglogboek op
  "Ploegcode"; daar staat wat de pagina wél teruggaf.
