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
  `_elev_cache`, `_names_cache`, `_channels_cache`, `_sprints_cache`,
  `_prevrank_cache`, `_roster_cache` (dict per koers), `_other_cache`.
  `_elev_cache` heeft `(etappe, aantal punten)` als sleutel: dezelfde etappe
  wordt als komende dag met 60 punten opgehaald en als getoonde etappe met
  200. Stond alleen de URL in de sleutel, dan kreeg het grote profiel de
  kleine versie terug. `_gpx_beschikbaar` houdt los bij of een etappe een
  profiel heeft, want `_gpx_rang` heeft dat nodig om te kiezen wélke koers
  getoond wordt.

### Keuze van de getoonde koers

Mannen en vrouwen koersen vaak tegelijk. De tegel toont er één, gekozen op:

1. eerstvolgende etappedatum
2. koers mét hoogteprofiel (`_gpx_rang`)
3. bij gelijke stand de mannen

De tweede koers komt terug via `_other_block` → `other_label`, `other_result`,
`other_gc`. Het overzicht "Komende dagen" toont álle koersen door elkaar.

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

## Diagnose-attributen

Deze zitten er puur om problemen op te sporen en mogen weg zodra het stabiel is:
`gpx_diag`, `times_diag`, `names_diag`, `gain_headers`, `gain_raw`,
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

## Openstaande punten

- Categorieën van cols ontbreken vaak vóór de koers (PCS publiceert ze pas na
  afloop via het bergklassement). Uitzoeken of het elders vooraf beschikbaar is.
- Een aantal cyclingstage-namen voor vrouwenklassiekers is een educated guess
  (`CYCLINGSTAGE_ONEDAY`); daarom staan er meerdere kandidaten per koers.
- De config flow is niet in een draaiende Home Assistant beproefd: de tests
  bouwen het optieschema op met gestubde HA-modules, wat niets zegt over de
  vraag of het scherm verschijnt en de entry laadt.
- Overweeg de diagnose-attributen te verwijderen zodra alles stabiel draait.
