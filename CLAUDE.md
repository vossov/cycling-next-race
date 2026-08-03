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
en het optiescherm) en `__init__.py` (config entry opzetten en herladen).

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

## Diagnose-attributen

Deze zitten er puur om problemen op te sporen en mogen weg zodra het stabiel is:
`gpx_diag`, `times_diag`, `names_diag`, `gain_headers`, `gain_raw`,
`names_fixed`, `gains_set`, `roster_size`, `elevation_source`.

## Dashboard

De Lovelace-kaarten staan in `lovelace/` en vallen **buiten HACS**; die zet je
zelf in de raw-config van het dashboard.

- `button_card_templates.yaml` → drie button-card-templates
  (`cycling_profile` tegel, `cycling_detail` pop-up, `cycling_upcoming`)
- `dashboard.yaml` → de complete opstelling: de conditionele tegel en de
  Bubble Card-pop-up met alle markdown-kaarten erin

`tests/test_dashboard.py` controleert dat elk attribuut dat een kaart
opvraagt ook echt door `sensor.py` wordt gezet, dat gebruikte templates
bestaan, en dat tegel en pop-up dezelfde hash delen.

Benodigde frontend-kaarten: button-card, card-mod, Bubble Card.

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
