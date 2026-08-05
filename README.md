# Cycling Next Race

Home Assistant-integratie die de eerstvolgende WorldTour-wielerwedstrijd op je
dashboard zet — met hoogteprofiel, cols, tussensprint, uitslagen, klassementen
en de Nederlandse tv-zenders.

Standaard worden de mannen- en de vrouwen-WorldTour gevolgd; in de
instellingen vink je zelf aan welke niveaus meedoen en welke daarvan alleen
in de pop-up mogen — zie [Welke niveaus je
volgt](#welke-niveaus-je-volgt). Koersen tegelijk? Dan toont de tegel er één:
eerst de eerstvolgende etappe, dan de koers met een hoogteprofiel, en bij
gelijke stand de mannen. De andere koers is in de pop-up aan te klikken:
bovenin staat een knop per koers, in de kleur van de leiderstrui, en je
krijgt er hetzelfde volledige beeld van — etappe met hoogteprofiel en
starttijd, waar hij te zien is, komende dagen, uitslag en alle vier de
klassementen met dagwinst. De koers van de tegel staat standaard open.

## Wat het laat zien

- **Hoogteprofiel** uit de echte GPX (cyclingstage), met vormbehoudende
  reductie zodat toppen niet wegvallen
- **Cols** met naam, categorie, lengte en stijgingspercentage
- **Tussensprint(en)** uit het officiële tijdschema
- **Start- en verwachte finishtijd**, gescrapet waar beschikbaar
- **Uitslag en klassementen** (algemeen, punten, berg, jongeren) met
  positieverandering, dagwinst en de ploeg achter elke renner
- **Live positie** van het peloton tijdens de koers
- **Tv-zenders** met uitzendtijden (wielerflits; alleen de Nederlandse
  uitzendingen worden getoond)
- **Watchscore** 1–10: een inschatting van hoe de moeite waard een etappe is

Is er geen data, dan toont de integratie niets in plaats van iets verzonnens.
Geen GPX betekent geen hoogtelijn, en geen profielgegevens betekent geen
watchscore. Zo ook de kleur van de leiderstrui op de koersknoppen: die staat
in een vaste lijst met koersen waarvan de kleur vaststaat (geel voor de Tour,
roze voor de Giro, rood voor de Vuelta, en zo verder). Een koers die er niet
in staat krijgt de gewone accentkleur — liever geen kleur dan een gegokte.

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
| Niveaus op het dashboard | WorldTour mannen + vrouwen |
| Niveaus alleen in de pop-up | geen |
| Aantal koersen naast de getoonde in de pop-up | 2 |

Wijzigingen gaan meteen in; de integratie herlaadt zichzelf.

### Welke niveaus je volgt

Je vinkt aan welke niveaus meedoen. Er zijn er vier:

- WorldTour mannen
- WorldTour vrouwen
- ProSeries mannen
- ProSeries vrouwen

Dat gebeurt in twee lijstjes. **Niveaus op het dashboard** mogen de tegel
pakken én staan in de pop-up; standaard zijn dat de twee WorldTours, precies
zoals het altijd was. **Niveaus alleen in de pop-up** komen er als knop bij,
maar blijven van de tegel af.

Wil je bijvoorbeeld de Ronde van Denemarken volgen zonder dat je dashboard
verandert: zet *ProSeries mannen* bij het tweede lijstje. Die koersen krijgen
dan een eigen knop in de pop-up, met uitslag, klassementen, tv-zenders en
hoogteprofielen, terwijl de tegel de WorldTour blijft tonen.

Lopen er meer koersen tegelijk dan er knoppen passen, dan gaan de niveaus van
het dashboard voor. Met *Aantal koersen naast de getoonde* bepaal je hoeveel
knoppen er naast de tegelkoers passen.

> **Let op bij ProSeries.** De WorldTour-nummers waarmee de kalender wordt
> opgehaald zijn nagekeken op procyclingstats, die van ProSeries niet. Levert
> een niveau geen koersen op, dan staat dat in het logboek én in het attribuut
> `levels_diag` van de sensor (**Ontwikkelhulpmiddelen → Statussen**), met het
> aantal koersen per niveau. Staat daar `ProSeries mannen: 0` terwijl er wel
> koersen zijn, dan klopt het nummer niet; het is één regel in
> `NIVEAUS` in `const.py`.

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
| `view` | `profile` | `profile` toont het hoogteprofiel, `countdown` een regel met het aftellen |
| `visible_days` | `2` (`0` bij `countdown`) | vanaf hoeveel dagen voor de koers de kaart verschijnt; `0` is altijd |
| `details` | `true` | een tik opent het detailvenster |

Lopen er meerdere koersen tegelijk, dan staan ze in dat detailvenster als
knoppen naast elkaar; de koers van de tegel staat open en de andere zijn
één tik ver. Is er maar één koers, dan is er niets extra's te zien.

### Voorbeelden

Alles wat je kunt instellen, met de standaardwaarden erbij:

```yaml
type: custom:cycling-next-race-card
entity: sensor.cycling_next_race   # welke sensor
view: profile                      # of: countdown
visible_days: 2                    # vandaag en morgen
details: true                      # tik opent het detailvenster
```

**Het profiel al een week vooruit.** Handig als je wilt zien wat eraan komt:

```yaml
type: custom:cycling-next-race-card
visible_days: 7
```

**Een aftelregel die er altijd staat.** Deze weergave is compact: de
koersnaam, de datum en hoeveel dagen het nog duurt — of `Bezig — dag 14/21`
tijdens een ronde. Ook buiten het seizoen blijft hij staan, zodat je met een
tik de uitslag van de laatste koers kunt bekijken:

```yaml
type: custom:cycling-next-race-card
view: countdown
```

`visible_days` staat bij deze weergave standaard op `0`, dus je hoeft niets
extra's in te stellen.

**De twee samen**, wat waarschijnlijk het prettigst werkt: een aftelregel die
altijd zichtbaar is, met daarboven het profiel zodra de koers dichtbij is.

```yaml
type: vertical-stack
cards:
  - type: custom:cycling-next-race-card
    view: profile
    visible_days: 2
  - type: custom:cycling-next-race-card
    view: countdown
```

De profielkaart verbergt zichzelf buiten die twee dagen, dus dan blijft
alleen de aftelregel over.

**Alleen de tegel, zonder venster** — handig op een tablet waar je niet wilt
dat er iets opengaat bij een aanraking:

```yaml
type: custom:cycling-next-race-card
details: false
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
   `Lovelace-kaart aangemeld via ... op /cycling_next_race/...`. Staat er in plaats
   daarvan `Kaartbestand niet gevonden`, dan mist `www/` in je installatie:
   controleer of `custom_components/cycling_next_race/www/` bestaat en
   installeer anders opnieuw via HACS.
4. **Leeg de browsercache.** De frontend bewaart scripts hardnekkig. Een
   harde herlaad (Ctrl+Shift+R, op mobiel de app-cache legen) haalt de kaart
   alsnog op. Dit is verreweg de meest voorkomende oorzaak vlak na een
   installatie.

### "Configuratiefout" die na verversen weg is

Zie je op de plek van de kaart een rood vlak met *Configuratiefout*, en is
dat na een keer verversen verdwenen, dan heeft Home Assistant de kaart
willen tekenen voordat het script geladen was. De frontend wacht daar maar
kort op; komt het net te laat, dan valt hij terug op een foutkaart.

Het gaat vanzelf over zodra het script in de cache van de browser staat, dus
je ziet het vooral één keer na een update.

Sinds versie 0.4 zet de integratie de kaart in de resourcelijst van
Lovelace in plaats van hem los mee te geven. Lovelace laadt zijn resources
en wacht daarop vóór het tekenen, waardoor die race weg is. Alleen in
YAML-modus kan dat niet — daar beheer je de lijst zelf — en blijft de oude
weg over.

Zie je het toch nog, open het dashboard dan op een computer in plaats van in
de app. De foutkaart toont daar de melding, en in de ontwikkelaarsconsole
(F12) staat de precieze reden. *Custom element doesn't exist* betekent dat
het script te laat was; een andere melding betekent dat er werkelijk iets
mis is met de configuratie en dat verversen niet helpt. In de mobiele app is
die melding niet op te vragen — tikken op de foutkaart doet daar niets.

De kaart-URL draagt een korte hash van het bestand, dus na een update haalt
de browser gegarandeerd de nieuwe versie op in plaats van een oude uit de
cache.

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
| `LEIDERSTRUI` | kleur van de leiderstrui per koers, voor de knoppen in de pop-up |

En in `const.py`:

| Constante | Betekenis |
|---|---|
| `NIVEAUS` | de niveaus met hun circuitnummer bij procyclingstats |

## Versies en updates

Elke release krijgt een tag als `v0.4.0`; HACS toont die naam en je kunt
ermee terug naar een eerdere versie. Zonder release valt HACS terug op de
laatste commit en zie je een hash staan.

Een nieuwe versie uitbrengen gaat zo:

1. Verhoog `version` in `custom_components/cycling_next_race/manifest.json`
   en `VERSION` in `const.py` — een test bewaakt dat die twee gelijk blijven.
2. Zet die wijziging op `main`.
3. `git tag v0.4.0 && git push origin v0.4.0`

De release-workflow controleert of de tag en de manifest dezelfde versie
noemen en publiceert daarna de release met notities uit de commits. Lopen
ze uiteen, dan faalt hij: anders installeert HACS `v0.5.0` terwijl Home
Assistant `0.4.0` rapporteert.

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
