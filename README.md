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

### Overstappen vanaf de YAML-configuratie

Stond dit in je `configuration.yaml`?

```yaml
sensor:
  - platform: cycling_next_race
```

Dan wordt die bij de eerstvolgende herstart automatisch omgezet naar een
integratie in de interface. Haal de regels daarna weg.

## Dashboard

De kaarten vallen buiten HACS: de integratie levert alleen de sensor, de
opmaak zet je zelf in je dashboard. Benodigd zijn
[button-card](https://github.com/custom-cards/button-card),
[card-mod](https://github.com/thomasloven/lovelace-card-mod) en
[Bubble Card](https://github.com/Clooos/Bubble-Card) voor de pop-up.

**1. Templates registreren.** Neem de inhoud van
[`lovelace/button_card_templates.yaml`](lovelace/button_card_templates.yaml)
over in de raw-configuratie van je dashboard (rechtsboven → *Raw
configuration editor*). Het `button_card_templates:`-blok staat op het
hoogste niveau, náást `views:`.

**2. Kaarten plaatsen.** Elke template is een button-card die zijn gegevens
uit de sensor haalt:

```yaml
# hoogteprofiel-tegel
type: custom:button-card
template: cycling_profile
entity: sensor.cycling_next_race

# groter profiel met colnamen, voor in de pop-up
type: custom:button-card
template: cycling_detail
entity: sensor.cycling_next_race

# overzicht "Komende dagen"
type: custom:button-card
template: cycling_upcoming
entity: sensor.cycling_next_race
```

**3. De kaarten zelf.** De complete opstelling staat in
[`lovelace/dashboard.yaml`](lovelace/dashboard.yaml): de tegel voor je
dashboard en de pop-up die opengaat als je erop tikt. Kopieer ze in een
view — niet in het `button_card_templates:`-blok, daar horen alleen de
templates uit stap 1.

De tegel is een `conditional` die pas verschijnt als de koers vandaag of
morgen is. Wil je hem altijd zien, laat dat omhulsel dan weg en houd het
`card:`-gedeelte over.

De pop-up bevat het grote profiel, de tv-zenders, "Komende dagen", en
daaronder de uitslag en de klassementen. Elke markdown-kaart verbergt
zichzelf als zijn attribuut leeg is, dus buiten een ronde blijft de pop-up
vanzelf kort.

Tegel en pop-up vinden elkaar via de hash `#cycling`; wijzig je die, doe het
dan op beide plekken.

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
