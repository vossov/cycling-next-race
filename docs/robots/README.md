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
