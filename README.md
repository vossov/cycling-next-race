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
toevoegen* en zoek op *Cycling Next Race*. In YAML is het:

```yaml
type: custom:cycling-next-race-card
```

Meer valt er niet in te stellen, maar het kan:

| Optie | Standaard | Betekenis |
|---|---|---|
| `entity` | `sensor.cycling_next_race` | de sensor |
| `details` | `true` | een tik opent het volledige overzicht |
| `always_show` | `false` | ook tonen als de koers verder weg is dan morgen |

De kaart toont het hoogteprofiel met de cols, de tussensprint, de
start- en verwachte finishtijd en de watchscore. Tikken opent een venster
met het grote profiel, de tv-zenders, de komende dagen, de dag-uitslag en
de klassementen. Onderdelen zonder gegevens blijven weg — buiten een ronde
is het venster vanzelf kort.

Standaard verschijnt de kaart pas als de koers vandaag of morgen is. Wil je
hem het hele seizoen zien, zet dan `always_show: true`.

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
