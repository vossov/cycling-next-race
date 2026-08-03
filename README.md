# Cycling Next Race

Home Assistant-integratie die de eerstvolgende WorldTour-wielerwedstrijd op je
dashboard zet — met hoogteprofiel, cols, tussensprint, uitslagen, klassementen
en de Nederlandse tv-zenders.

Zowel de mannen- als de vrouwen-WorldTour worden gevolgd — op dit moment
alleen die twee kalenders; de opzet laat ruimte om er later andere koersen
naast te zetten. Koersen tegelijk? Dan toont de tegel er één: eerst de
eerstvolgende etappe, dan de koers met een hoogteprofiel, en bij gelijke
stand de mannen. De andere koers verschijnt met zijn dag-uitslag in de
pop-up.

## Wat het laat zien

- **Hoogteprofiel** uit de echte GPX (cyclingstage), met vormbehoudende
  reductie zodat toppen niet wegvallen
- **Cols** met naam, categorie, lengte en stijgingspercentage
- **Tussensprint(en)** uit het officiële tijdschema
- **Start- en verwachte finishtijd**, gescrapet waar beschikbaar
- **Uitslag en klassementen** (algemeen, punten, berg, jongeren) met
  positieverandering en dagwinst
- **Live positie** van het peloton tijdens de koers
- **Tv-zenders** met uitzendtijden (wielerflits; alleen de Nederlandse
  uitzendingen worden getoond)
- **Watchscore** 1–10: een inschatting van hoe de moeite waard een etappe is

Is er geen data, dan toont de integratie niets in plaats van iets verzonnens.
Geen GPX betekent geen hoogtelijn, en geen profielgegevens betekent geen
watchscore.

## Installatie via HACS

1. HACS → rechtsboven de drie puntjes → **Aangepaste repositories**
2. Plak de URL van deze repo, categorie **Integration**, en klik toevoegen
3. Zoek op *Cycling Next Race*, installeer, en herstart Home Assistant

De Python-afhankelijkheid (`procyclingstats`) installeert Home Assistant
automatisch.

## Handmatige installatie

Kopieer `custom_components/cycling_next_race/` naar de map
`custom_components/` van je Home Assistant en herstart.

## Configuratie

Ga naar **Instellingen → Apparaten & Services → Integratie toevoegen**, zoek
op *Cycling Next Race* en bevestig. Er valt niets in te vullen: de
integratie heeft geen sleutel of adres nodig.

De sensor heet daarna `sensor.cycling_next_race`.

### Instellingen

Achter **Configureren** bij de integratie stel je in:

| Instelling | Standaard |
|---|---|
| Aantal renners in de uitslag | 10 |
| Aantal renners in het klassement | 10 |
| Maximaal aantal komende etappes | 10 |
| Komende etappes tonen tot (dagen vooruit) | 7 |
| Verversen elke (minuten) | 30 |
| Verversen tijdens een koers (minuten) | 5 |

Wijzigingen gaan meteen in; de integratie herlaadt zichzelf.

## Dashboard

De kaart zit in de integratie: je hoeft geen resources te registreren, geen
templates in de raw-config te plakken en geen extra frontend-kaarten te
installeren.

**Voeg hem toe zoals elke andere kaart.** Bewerk je dashboard, kies *Kaart
toevoegen* en zoek op *Cycling Next Race*. De kaart heeft een eigen
instelscherm: de sensor staat er al in en de twee schakelaars zet je met een
klik. YAML komt er niet aan te pas.

Liever toch typen? Dit volstaat:

```yaml
type: custom:cycling-next-race-card
```

De sensor wordt vanzelf gevonden.

| Optie | Standaard | Betekenis |
|---|---|---|
| `entity` | `sensor.cycling_next_race` | welke sensor de kaart uitleest |
| `details` | `true` | een tik opent het detailvenster |
| `always_show` | `false` | ook tonen als de koers verder weg is dan morgen |

### Voorbeelden

Alles wat je kunt instellen, met de standaardwaarden expliciet erbij:

```yaml
type: custom:cycling-next-race-card
entity: sensor.cycling_next_race   # welke sensor
details: true                      # tik opent het detailvenster
always_show: false                 # alleen tonen bij een koers vandaag of morgen
```

Het hele seizoen zichtbaar, ook als de eerstvolgende koers nog dagen weg is:

```yaml
type: custom:cycling-next-race-card
always_show: true
```

Alleen de tegel, zonder venster — handig op een tablet waar je niet wilt
dat er iets opengaat bij een aanraking:

```yaml
type: custom:cycling-next-race-card
details: false
```

De kaart binnen een sectie of grid, met een vaste breedte:

```yaml
type: custom:cycling-next-race-card
grid_options:
  columns: 12
  rows: auto
```

Wil je hem in een eigen pop-up of naast andere kaarten, dan gedraagt hij
zich als elke gewone kaart en kun je hem in `vertical-stack`, `grid` of een
Bubble Card-pop-up zetten:

```yaml
type: vertical-stack
cards:
  - type: custom:cycling-next-race-card
    details: false
  - type: markdown
    content: Volg de koers live op procyclingstats.com
```

### Zo ziet het eruit

Een indruk van de tekstblokken in het detailvenster. De namen hieronder zijn
ter illustratie; de kaart toont alleen wat de bronnen werkelijk leveren.

```
Etappe 13 · uitslag
 1  Pogacar Tadej          4:12:33
 2  Vingegaard Jonas         +0:14
 3  Evenepoel Remco          +1:18

Algemeen klassement
 1  Pogacar Tadej         52:14:33
 2  Vingegaard Jonas   +2:12 ▲1 −0:14
 3  Evenepoel Remco    +4:39 ▼1 +1:18

Puntenklassement
 1  Philipsen Jasper       302 +25

Bergklassement
 1  Ciccone Giulio       84 ▲2 +10
```

Achter een klassement staat de positieverandering ten opzichte van de vorige
etappe (▲ gestegen, ▼ gedaald) en wat er die dag is gewonnen of verloren —
in tijd bij het algemeen en jongerenklassement, in punten bij de andere twee.

De tv-zenders staan als regel bovenaan het venster, met het zenderlogo waar
wielerflits dat meelevert:

```
NPO 1 14:15  ·  Eurosport 1 12:45
```

Alleen Nederlandse uitzendingen, en alleen als de koers binnen zes dagen
begint — verder vooruit publiceert de gids niets.

### De kaart verschijnt niet

De integratie meldt de kaart aan zodra hij geladen wordt. Loopt dat mis, dan
werkt de sensor gewoon door en zie je alleen de kaart niet. Loop dit na:

1. **Staat de integratie er?** Instellingen → Apparaten & Services. Zonder
   toegevoegde integratie draait de aanmelding niet. De sensor
   `sensor.cycling_next_race` hoort te bestaan.
2. **Kun je het bestand ophalen?** Open
   `http://<jouw-ha>:8123/cycling_next_race/cycling-next-race-card.js` in je
   browser. Zie je JavaScript, dan is de aanmelding gelukt en zit het
   probleem in de browser (stap 4). Krijg je een 404, dan is het bestand niet
   geserveerd — ga naar stap 3.
3. **Wat zegt het logboek?** Zoek op `cycling_next_race`. Bij succes staat er
   `Lovelace-kaart aangemeld op /cycling_next_race/...`. Staat er in plaats
   daarvan `Kaartbestand niet gevonden`, dan mist `www/` in je installatie:
   controleer of `custom_components/cycling_next_race/www/` bestaat en
   installeer anders opnieuw via HACS.
4. **Leeg de browsercache.** De frontend bewaart scripts hardnekkig. Een
   harde herlaad (Ctrl+Shift+R, op mobiel de app-cache legen) haalt de kaart
   alsnog op. Dit is verreweg de meest voorkomende oorzaak vlak na een
   installatie.

### De oude opzet met button-card

Vóór deze kaart werden de profielen als button-card-templates meegeleverd.
Die staan er nog, voor wie zijn dashboard zo heeft ingericht: zie
[`lovelace/`](lovelace/). Nieuw beginnen doe je met de kaart hierboven —
die heeft button-card, card-mod noch Bubble Card nodig.

## Instellingen in de code

Wat niet in de interface staat, staat bovenin `sensor.py`:

| Constante | Betekenis |
|---|---|
| `GPX_OVERRIDE` | eigen GPX-adres per koers, als er geen publieke is |
| `CYCLINGSTAGE_ROUTE`, `CYCLINGSTAGE_ONEDAY` | adressen van de etappeteksten per koers |

## Bronnen

- [procyclingstats.com](https://www.procyclingstats.com) — kalender, uitslagen,
  klassementen, cols, live-positie
- [cyclingstage.com](https://www.cyclingstage.com) — GPX-routes, tijdschema's
  met tussensprint, etappeteksten met colnamen en finishtijd
- [wielerflits.nl](https://www.wielerflits.nl) — tv-gids

Deze integratie schraapt publieke webpagina's. Verandert een van die sites zijn
opbouw, dan kan een onderdeel wegvallen; de integratie laat dat onderdeel dan
leeg in plaats van te raden.

## Licentie

MIT — zie [LICENSE](LICENSE). Gebruik, aanpassen en doorgeven mag, ook
commercieel; de licentietekst moet meeliften en er is geen garantie.

## Ontwikkelen

```bash
pip install pytest
pytest tests/          # pure functies, geen netwerk nodig
```

Zie [CLAUDE.md](CLAUDE.md) voor de architectuur, de gebruikte bronnen en de
valkuilen die je moet kennen voordat je iets wijzigt.
