# robots.txt van de bronnen, zoals opgehaald op 7 september 2026

Door de eigenaar opgehaald en hier geplakt: de proxy in de
ontwikkelomgeving laat deze sites niet door. De analyse staat in CLAUDE.md
onder "Wat de robots.txt van onze bronnen zegt".

Haal ze opnieuw op als er iets aan de integratie verandert dat een ánder
pad raakt dan wat er nu wordt opgehaald — een robots.txt is geen
eenmalige controle.

## racecenter.lavuelta.es — 404 (7 september 2026)

Er is geen robots.txt op dat subdomein. Volgens RFC 9309 §2.3.1.3 mag een
client bij een 4xx-status aannemen dat er geen restricties zijn.

Wat dat wél en niet zegt:

- **niet verboden** — er is geen regel die ons of wie dan ook iets ontzegt;
- **niet toegestaan** — het is geen uitnodiging, alleen de afwezigheid van
  een verbod. `racecenter.lavuelta.es` is bovendien een subdomein; het
  hoofddomein `lavuelta.es` kan een eigen bestand hebben dat hier niet geldt
  maar wel iets zegt over de bedoeling. Dat is niet nagekeken.

Voor een live-feed komt daar nog iets bij dat robots.txt helemaal niet
regelt: het verzoekpatroon. Een kalenderpagina is één verzoek per dag, een
live-positie wil elke minuut ververst worden. Zie "Live: welke bron" in
CLAUDE.md.

## www.lavuelta.es — `Disallow: /api` (7 september 2026)

Het hoofddomein hééft wel een robots.txt, en daar staat onder
`User-agent: *`:

```
Disallow: /admin
Disallow: /sonatadmin
Disallow: /api
Disallow: /graphql
Disallow: /login
```

**`/api` is precies het pad dat een live-koppeling zou gebruiken**
(`/api/telemetryCompetitor-2026`, `/api/ranking-2026`).

Formeel geldt dit niet voor `racecenter.lavuelta.es`: robots.txt werkt per
host, en dat subdomein heeft er zelf geen (404). Maar dit is dezelfde
situatie als `Disallow: /images` bij cyclingstage, en scherper: daar ging
het om een sjabloonregel voor afbeeldingen, hier om precies het
gegevenspad, expliciet genoemd naast `/admin` en `/graphql`.

Wie hierop terugkomt: dit is een uitspraak van ASO over hoe zij hun API
bekeken willen zien. Een 404 op het subdomein is geen toestemming, en de
afwezigheid van een regel op de ene host weegt niet op tegen een expliciete
regel op de andere.

## Besluit van de eigenaar (7 september 2026)

**Wat niet expliciet verboden is, mag.** Een `Disallow` die op onze
user-agent en op ons pad slaat is een verbod; een afwezige regel, een regel
voor een andere bot, een regel op een ander subdomein of een
uitgecommentarieerde regel is dat niet.

Bij het omgekeerde uitgangspunt houdt de integratie op te bestaan: vrijwel
geen enkele site geeft expliciet toestemming, dus dan valt elke bron af.

Dat betekent: cyclingstage `/images` mag (die regels gelden voor googlebot
en anderen, niet voor ons), en ASO `racecenter.lavuelta.es/api` mag (dat
subdomein heeft geen robots.txt; de regel op `www.lavuelta.es` geldt daar
niet). FirstCycling blijft verboden — daar staat `Disallow: /` voor iedereen
én ClaudeBot bij naam.

Zie CLAUDE.md, "Wat 'verboden' betekent in dit project".
