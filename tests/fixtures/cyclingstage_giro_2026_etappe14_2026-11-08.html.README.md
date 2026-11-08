# cyclingstage_giro_2026_etappe14_2026-11-08.html

| | |
|---|---|
| **Adres** | https://www.cyclingstage.com/giro-2026-route/stage-14-italy-2026/ |
| **Opgehaald** | 2026-11-08T12:12:21+01:00 |
| **Antwoord** | HTTP 200, `text/html; charset=utf-8` |
| **Grootte** | 56,671 bytes |
| **SHA-256** | `35f214e136139668a8d9da7f7cf3ab0a8580bf85ed15b7af91ff4c3a4e0266ac` |

## Methode
curl met `--compressed`, `Accept-Language: nl,en;q=0.8` en user-agent `Mozilla/5.0 (compatible; cycling-next-race-research/2026-11; +https://github.com/vossov/cycling-next-race)`. De body is ongewijzigd opgeslagen.

## Inhoud in de ruwe bron?
Ja. Gezocht op "intermediate sprint at kilometre 116.0" en "stage-14-parcours.gpx": gevonden.

## Velden
- Tekst: datum, afstand (`133 kilometres`), klimmen met lengte en stijging, **`Time bonuses of 6, 4 and 2 seconds are up for grabs at the intermediate sprint at kilometre 116.0`**
- Afbeeldingen in `cdn.cyclingstage.com/images/giro-italy/2026/`: `stage-14-profile.jpg`, `-profile-finale.jpg`, `-route.jpg`, `-route-finale.jpg`, foto's per col (`stage-14-pila.jpg`, `-verrogne.jpg`, `-barthelemy.jpg`), tracker-gifs
- GPX `stage-14-parcours.gpx`
- **Link "timings" naar `/images/giro-italy/2026/stage-14-times.jpg`** (zie de aparte fixture)
- Kaart via `map-iframe.php?post=secure.tourtrackerdata.com/widgets/...type=map&tour_id=1335&stage_number=14`

## Bijzonderheden
- Gevraagd in `docs/gevraagde-paginas.md` van de repo (2.2 en 3.4): het tijdschema **bestaat**, maar als **JPG** (`stage-{n}-times.jpg`), niet als `stage-{n}-times.htm`. De pagina linkt er zelf naar (titel "timings"), dus het adres hoeft niet geraden te worden.
- **Let op:** "intermediate sprint at kilometre 116.0" is volgens de cronotabella de **Red Bull-kilometer**; de echte tussensprint (`S`) ligt op km 53,9 in Roisan.
- Geen start- of finishtijd in de tekst (pagina is na afloop bijgewerkt: "link to stage results added").
- `secure.tourtrackerdata.com` (RCS-tracker) heeft `User-agent: *` / `Disallow: /`: niet bruikbaar.
