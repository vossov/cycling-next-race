# Cycling Next Race

Home Assistant-integratie die de eerstvolgende WorldTour-wielerwedstrijd op je
dashboard zet — met hoogteprofiel, cols, tussensprint, uitslagen, klassementen
en de Nederlandse tv-zenders.

Zowel de mannen- als de vrouwen-WorldTour worden gevolgd. Koersen tegelijk?
Dan toont de tegel er één: eerst de eerstvolgende etappe, dan de koers met een
hoogteprofiel, en bij gelijke stand de mannen. De andere koers verschijnt met
zijn dag-uitslag in de pop-up.

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

In `configuration.yaml`:

```yaml
sensor:
  - platform: cycling_next_race
```

Dat is alles. De sensor heet `sensor.volgende_wielerkoers`.

## Dashboard

De kaarten zijn losse Lovelace-templates; die vallen buiten HACS en zet je
zelf in je dashboard. Ze staan in [`lovelace/button_card_templates.yaml`](lovelace/button_card_templates.yaml)
en horen in de raw-config van je dashboard onder `button_card_templates:`.

Benodigd: [button-card](https://github.com/custom-cards/button-card),
[card-mod](https://github.com/thomasloven/lovelace-card-mod) en
[Bubble Card](https://github.com/Clooos/Bubble-Card) voor de pop-up.

## Instellingen in de code

Bovenin `sensor.py` staan een paar constanten die je kunt aanpassen:

| Constante | Betekenis |
|---|---|
| `RESULT_N`, `GC_N` | aantal renners in uitslag en klassement |
| `UPCOMING_N`, `UPCOMING_DAYS` | omvang van het overzicht "Komende dagen" |
| `SCAN_INTERVAL`, `LIVE_SCAN_INTERVAL` | verversfrequentie (normaal / tijdens de koers) |
| `GPX_OVERRIDE` | eigen GPX-adres per koers, als er geen publieke is |

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
