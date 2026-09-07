# cyclingstage_wk_2026_canada.html

`https://www.cyclingstage.com/world-championships-2026-canada/`, opgehaald
7 september 2026.

Een van de zes koersen waarvan de kalender geen routeadres geeft. Deze
fixture laat zien dat de terugval van 0.24 hier **niet** werkt, en waarom:

- De koerspagina linkt naar géén enkele subpagina onder
  `/world-championships-2026-canada/`, dus `route_kandidaten` vindt niets.
- De programmatabel staat op de koerspagina zelf, maar met een ándere
  kolomindeling: `datum | start - finish | type | km | el.gain`. Er is geen
  nummerkolom, want het zijn geen etappes maar onderdelen (ITT vrouwen, ITT
  mannen, mixed relay, wegrace vrouwen, wegrace mannen).
- In die tabel staat geen enkele link, dus zelfs met een aangepaste parser
  is er geen etappe-URL om een uitslag of profiel mee op te halen.

`parse_etappes` geeft hier dus 0 etappes, en dat is voorlopig het juiste
antwoord: een koers zonder etappe-adressen levert niets op dat we kunnen
tonen. Wie dit wil oplossen heeft meer nodig dan deze pagina.
