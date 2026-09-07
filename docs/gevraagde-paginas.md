# Pagina's die deze integratie nodig heeft om te controleren

De ontwikkelomgeving komt **niet** bij cyclingstage.com, wielerflits.nl of de
racecenter-sites van ASO — de egress-proxy blokkeert ze. Elke parser die hier
gebouwd wordt moet daarom op HTML draaien die met de hand is opgeslagen.
Deze lijst staat op volgorde van wat het meest oplevert.

## De adressen, kopieerbaar

Stand 7 september 2026. Alles hieronder is een volledig adres — geen
sjablonen. Wat al binnen is staat verderop afgestreept.

### Deze week, want de Vuelta eindigt op 13 september

```
https://www.cyclingstage.com/vuelta-2026-results/
https://www.cyclingstage.com/vuelta-2026-gpx/
https://www.cyclingstage.com/images/vuelta/2026/stage-19-times.htm
https://www.cyclingstage.com/vuelta-2026-points-classification/
https://www.cyclingstage.com/vuelta-2026-kom-classification/
https://www.cyclingstage.com/vuelta-2026-favourites/
https://www.cyclingstage.com/vuelta-2026/vuelta-2026-withdrawals/
```

### Eendaagse koers — GP Québec rijdt 11 september

```
https://www.cyclingstage.com/gp-quebec-2026/
https://www.cyclingstage.com/gp-quebec-2026-results/
```

De tweede pas ná de koers, anders staat er nog geen uitslag op.

### Het WK, 20-27 september

```
https://www.cyclingstage.com/world-championships-2026-canada/
```

En de routepagina waar die naartoe linkt, wat dat adres ook blijkt te zijn.

### Tour of Britain — voorbij, de pagina's staan er nog

```
https://www.cyclingstage.com/tour-of-britain-2026/
https://www.cyclingstage.com/tour-of-britain-2026/route-gb-2026/
https://www.cyclingstage.com/tour-of-britain-2026-results/
```

### Een vrouwenkoers en een niet-Vuelta-etappe

```
https://www.cyclingstage.com/tour-of-flanders-2026-women/
https://www.cyclingstage.com/tour-of-flanders-2026-women/route-women-tof-2026/
https://www.cyclingstage.com/giro-2026-route/italy-route-2026/
```

Van die laatste ook één etappepagina, via een link op die routepagina.

### ASO live — tijdens een etappe

```
https://racecenter.lavuelta.es/api/telemetryCompetitor-2026
https://racecenter.lavuelta.es/api/ranking-2026
https://www.lavuelta.es/robots.txt
```

Weet je niet welk eindpunt: open `https://racecenter.lavuelta.es/en/`,
F12 -> Netwerk -> filter op `api`, en stuur de namen die voorbijkomen.

### Later, geen haast

```
https://www.wielerflits.nl/nieuws/wielrennen-op-tv/
```

Nogmaals, maar dan op een voorjaarsdag met de Ronde van Vlaanderen bij zowel
mannen als vrouwen — dat is het geval waar de koersherkenning op het geslacht
moet afgaan.

## Hoe opslaan

In Safari: **Archief → Bewaar als → Webarchief**. Dat werkte voor de
startlijst (`.webarchive` is een plist met de HTML erin, die hier uit te
pakken is). In Chrome of Firefox: **Pagina opslaan als → Volledige webpagina**,
of `Ctrl/Cmd+U` (broncode) en die tekst opslaan als `.html`.

Voor `robots.txt` en JSON-eindpunten volstaat kopiëren en plakken in een
bericht — dat is platte tekst.

Bij elke pagina staat hieronder wat er dan mee gebeurt en wat het oplost.

---

## Blok 1 — principieel, en het eerst

Hier hoort geen code op gebouwd te worden voordat dit is nagekeken. Het
project heeft FirstCycling op precies deze grond afgewezen (`Disallow: /`,
met ClaudeBot er apart bij naam in), en de bronnen die we **wél** gebruiken
zijn nooit gecontroleerd. Dat is een gat.

**AFGEROND op 7 september 2026.** De bestanden staan in `docs/robots/`, de
analyse in CLAUDE.md onder "Wat de robots.txt van onze bronnen zegt".

Uitkomst in het kort: wielerflits is in orde (de `*`-groep noemt een
padlijst zonder `Disallow: /`, en de tv-gids valt onder geen regel).
Cyclingstage heeft géén actieve `*`-groep — die staat uitgecommentarieerd —
dus formeel raakt geen enkele regel ons, en alle HTML-pagina's die we
ophalen zijn zelfs voor googlebot toegestaan. Maar `Disallow: /images` staat
in élk toegelaten blok, en daar hangen het hoogteprofiel en het tijdschema
onder. Besluit: laten staan, met een eerlijke user-agent (0.26.2).

De robots.txt van ASO (blok 4.1) staat nog open.

---

## Blok 2 — code die op verzonnen HTML draait

Deze parsers zijn nooit tegen een echte pagina gehouden. Het project heeft de
regel "nooit verzonnen HTML" juist omdat dat hier al twee keer een echte bug
heeft gemaskeerd.

### 2.1 De tv-gids van wielerflits — BINNEN (7 september 2026)

`tests/fixtures/wielerflits_tv_2026-09-07.html`. Meteen raak: de koppeling
was sinds 0.19 stuk (procyclingstats-padvorm), eendaagse koersen konden nooit
zenders krijgen, en koppelen op slug gaf de Giro d'Italia de uitzendtijden
van de Giro della Toscana. Alle drie gerepareerd in 0.26.3, met tests op deze
pagina.

**Nog wél nuttig, later:** een tweede tv-gids uit een ander deel van het
seizoen — een voorjaarsweekend met de klassiekers, of een dag met zowel een
mannen- als een vrouwenkoers van dezelfde naam (Ronde van Vlaanderen). Dat
laatste is het geval waar `_zelfde_koers` op het geslacht moet afgaan, en dat
staat nu alleen als losse eenheidstest.

### 2.2 Het tijdschema van een etappe

```
https://www.cyclingstage.com/images/vuelta/2026/stage-18-times.htm
```

(vervang `18` door een etappe die nog moet komen; zie de GPX-adressen in
`gpx_urls()` voor de slug van een andere koers)

Hieruit komt de **tussensprint**. `_parse_times` draait nu op een tabel die ik
zelf heb getypt.

### 2.3 De resultaten-overzichtspagina van een koers

```
https://www.cyclingstage.com/vuelta-2026-results/
```

Dit is de **terugval die 0.24 heeft toegevoegd** en die in 0.26.1 pas echt
ging werken. `parse_uitslag_index` leest hier het adres van elke etappe-uitslag
op. Hij is getest op links die toevallig in de routepagina stonden, maar de
indexpagina zelf is nooit gezien — de opmaak kan heel anders zijn.

Doe er ook een van een koers **buiten** de grote rondes bij, want juist die
46 koersen hebben deze terugval nodig:

```
https://www.cyclingstage.com/tour-of-britain-2026-results/
```

### 2.4 De GPX-overzichtspagina

```
https://www.cyclingstage.com/vuelta-2026-gpx/
```

De terugval als de vaste GPX-adressen niets opleveren — precies wat ons ooit
het profiel van de Vuelta kostte. `_parse_gpx_index` is zo ruim mogelijk
gehouden (elke href die op `.gpx` eindigt) en draait op synthetische HTML.

---

## Blok 3 — één fixture, dus één soort koers

Alles wat we van cyclingstage weten komt van de **Vuelta: mannen, grote
ronde**. Over de andere soorten koersen zegt dat niets, en die hebben
aantoonbaar andere adressen en soms andere opmaak.

### 3.1 Een routepagina van een koers zonder routeadres in de kalender

Zes koersen van 2026 hebben een lege routekolom. Voor die koersen zoekt de
integratie de etappetabel via een link op de koerspagina. Dat het adres
`route-gb-2026` heet komt uit een **zoekresultaat**, niet uit de pagina zelf.

Het WK is de enige meerdaagse koers uit dat lijstje die nog komt (20–27
september) en dus de enige manier om dit nog dit jaar te verifiëren:

```
https://www.cyclingstage.com/world-championships-2026-canada/
```

En de routepagina waar die naartoe linkt, wat dat adres ook blijkt te zijn.

Ter controle van de Tour of Britain-fix achteraf (de koers is voorbij, de
pagina staat er nog):

```
https://www.cyclingstage.com/tour-of-britain-2026/
https://www.cyclingstage.com/tour-of-britain-2026/route-gb-2026/
```

Blijkt dat tweede adres niet te bestaan, dan is de fix van 0.24 nooit
uitgekomen en moet er iets anders.

### 3.2 De resultatenpagina van een eendaagse koers

```
https://www.cyclingstage.com/gp-quebec-2026-results/
```

(11 september; Montréal is 13 september, Lombardije 10 oktober)

Een eendaagse koers heeft geen `stage-N`-pagina, dus zijn uitslag wordt op een
andere manier gezocht dan die van een etappe. Die weg is nooit tegen een echte
pagina gehouden.

### 3.3 Een startlijst van een ánder soort koers

De startlijstparser is gebouwd op de Vuelta. Twee tegenproeven:

```
https://www.cyclingstage.com/gp-quebec-2026/            (eendaags)
```
en de riders-pagina waar die naartoe linkt, plus:

```
https://www.cyclingstage.com/tour-of-flanders-2026-women/   (vrouwen, uit de kalender)
```

Bij een vrouwenkoers verwacht ik dezelfde opmaak maar 7 renners per ploeg in
plaats van 8 — als de parser daarop struikelt wil ik dat weten.

### 3.4 Een etappepagina van een andere koers dan de Vuelta

```
https://www.cyclingstage.com/tour-of-britain-2026/stage-4-gb-2026/
```

Hieruit komen de **colnamen**, de starttijd en de verwachte finishtijd. Dat is
alleen op een Vuelta-etappe getest, en de adressen van etappeteksten volgen
géén vast patroon.

---

## Blok 4 — nieuwe functionaliteit

### 4.1 Live: ASO Race Center

Dit is het antwoord op "live koersen doen het niet meer".

**De robots.txt gaf een 404 (7 september 2026).** Volgens RFC 9309 mag een
client daaruit afleiden dat er geen restricties zijn — geen verbod dus, maar
ook geen uitnodiging. Zie `docs/robots/README.md`.

Wat er nog nodig is, **tijdens een etappe** (dus terwijl er
gereden wordt, anders is de feed leeg):

```
https://racecenter.lavuelta.es/api/telemetryCompetitor-2026
https://racecenter.lavuelta.es/api/ranking-2026
```

Openen in een browsertab en de JSON kopiëren. Weet je niet welk eindpunt het
is: open `https://racecenter.lavuelta.es/en/`, druk F12 → tabblad **Netwerk**,
filter op `api`, en stuur de namen die voorbijkomen. Eén schermafbeelding van
die lijst is al genoeg om verder te kunnen.

Waarom dit de moeite waard is: één parser bedient acht koersen (Tour, Vuelta,
Dauphiné, Parijs-Nice, Parijs-Roubaix, Luik, Flèche, Tour de France Femmes),
en de vorm van het eindpunt staat al vast dankzij de etappelijst die je eerder
gaf.

### 4.2 De favorietenpagina van een koers

```
https://www.cyclingstage.com/vuelta-2026-favourites/
```

Dit kan de vraag beantwoorden waar ik nu bewust omheen loop: **wie ertoe doet
in een koers.** Het rugnummer mag daar niet voor gebruikt worden (dat is
alfabetisch, zie CLAUDE.md), maar als cyclingstage zelf een favorietenlijst
publiceert is dat een echte bron in plaats van een afleiding.

Ik weet niet of het een leesbare lijst is of een lopend verhaal — dat bepaalt
of er iets mee kan.

### 4.3 De uitvallerspagina

```
https://www.cyclingstage.com/vuelta-2026/vuelta-2026-withdrawals/
```

De startlijst markeert uitvallers al met een doorhaling, maar het tijdstempel
daarbij klopt niet (negen renners bij acht ploegen delen dezelfde seconde).
Deze pagina zou de echte reden en het echte moment kunnen geven.

### 4.4 De klassementspagina's

```
https://www.cyclingstage.com/vuelta-2026-points-classification/
https://www.cyclingstage.com/vuelta-2026-kom-classification/
```

Op 23 augustus stond hier alleen de puntenverdeling, met de mededeling dat de
standen "in a table during La Vuelta" zouden komen. De Vuelta is nu bijna
afgelopen — als ze er inmiddels staan, kunnen het punten- en bergklassement
terug. De herkenning ligt klaar in `_KLASSEMENTEN`; er hoeft geen code bij.

---

## Wat ik met elke pagina doe

1. HTML in `tests/fixtures/` met een `.README.md` ernaast: waar hij vandaan
   komt, wanneer hij is opgeslagen, en wat er in staat.
2. Parser ertegenaan, met een test per randgeval dat de pagina zelf oplevert.
3. Wat de pagina niet geeft, blijft leeg — niets afleiden.

## Wat het minst nodig is

Voor de volledigheid, zodat je niet meer opslaat dan zinvol: de kalenderpagina,
de routepagina van de Vuelta, een Vuelta-etappepagina, een Vuelta-etappe-uitslag
en de Vuelta-startlijst hebben we al. Die hoeven niet opnieuw, tenzij je
vermoedt dat de opmaak is veranderd.
