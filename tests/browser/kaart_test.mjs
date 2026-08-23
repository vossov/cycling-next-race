/*
 * Rendert de kaart in Chromium met synthetische attributen en controleert
 * op JS-fouten, NaN/undefined en of de onderdelen getekend worden.
 *
 * Draait niet in CI (Playwright is daar te zwaar); handmatig:
 *
 *   npm install playwright
 *   node tests/browser/kaart_test.mjs
 *
 * Het pad naar Chromium staat hieronder en verschilt per installatie.
 */
import { chromium } from 'playwright';
import fs from 'fs';

const KAART = new URL('../../custom_components/cycling_next_race/www/cycling-next-race-card.js', import.meta.url).pathname;

// Synthetische attributen: een bergetappe met alles erop en eraan.
const attrs = {
  show_state: 'Vandaag', days_until: 0, race_name: 'Tour de France',
  countdown: '🟢 Bezig — dag 14/21', date: '18 juli', type: 'Etappekoers',
  eyebrow: 'Etappe 14 · Tour de France', start_time: '12:50', finish_est: '17:12',
  departure: 'Pau', arrival: 'Luchon', distance_km: 170.9, vertical_m: 3800,
  profile_score: 438, watchability: 9,
  elevation: Array.from({ length: 80 }, (_, i) => [i * 2.15, 400 + 900 * Math.sin(i / 9) + 300 * Math.sin(i / 3)]),
  climbs: [
    { name: 'Col du Tourmalet', category: 'HC', km_to_finish: 60.2, top_m: 2115, length_km: 17.1, steepness_pct: 7.3 },
    { name: 'Peyresourde', category: '1', km_to_finish: 12.4, top_m: 1569, length_km: 9.7, steepness_pct: 7.8 },
  ],
  sprints: [56.1],
  // velden zoals _upcoming_entry ze zet: eyebrow, date, show_state, race_key
  // + etappegegevens
  upcoming: [
    { date: '2026-07-18', eyebrow: 'Etappe 15 · Tour de France', show_state: 'Morgen',
      race_key: 'tour-de-france', level: '1',
      departure: 'Loudenvielle', arrival: 'Plateau de Beille', distance_km: 197,
      vertical_m: 2400, profile_score: 402, watchability: 8 },
    { date: '2026-07-19', eyebrow: 'Etappe 4 · Tour de France Femmes · Dames', show_state: 'Overmorgen',
      race_key: 'tour-de-france-femmes', level: '24',
      departure: 'Saumur', arrival: 'Poitiers', distance_km: 130, vertical_m: 1500,
      profile_score: 120, watchability: 5 },
    { date: '2026-07-20', eyebrow: 'Etappe 5 · Tour de France Femmes · Dames', show_state: 'Za 20 jul',
      race_key: 'tour-de-france-femmes', level: '24',
      departure: 'Poitiers', arrival: 'Limoges', distance_km: 152, vertical_m: 1900,
      profile_score: 180, watchability: 6 },
  ],
  // zoals _races_block ze zet: de tegelkoers eerst (primary), daarna de
  // koersen die tegelijk lopen met hun eigen uitslag en standen
  races: [
    { primary: true, key: 'tour-de-france', label: 'Tour de France',
      race_name: 'Tour de France', women: false, level: '1', jersey: '#F3C700' },
    { key: 'tour-de-france-femmes', label: 'Tour de France Femmes · Dames',
      race_name: 'Tour de France Femmes', women: true, level: '24', jersey: '#F3C700',
      eyebrow: 'Etappe 4 · Tour de France Femmes · Dames', show_state: 'Overmorgen',
      days_until: 2,
      last_stage_label: 'Etappe 3 · Tour de France Femmes',
      // met team_code: die gaat voor op de volledige naam
      last_result: [
        { rank: 1, rider: 'Vollering Demi', team: 'FDJ', team_code: 'FST', time: '3:02:11' },
        { rank: 2, rider: 'Kopecky Lotte', team: 'SD Worx', team_code: 'SDW', time: '3:02:11' },
      ],
      gc_top: [
        { rank: 1, rider: 'Vollering Demi', team: 'FDJ', time: '9:14:02', move: 1, gain_s: -22 },
        { rank: 2, rider: 'Kopecky Lotte', team: 'SD Worx', time: '9:14:36', move: -1, gain_s: 22 },
      ],
      points_top: [{ rank: 1, rider: 'Wiebes Lorena', points: 120, move: 0, gain: 25 }],
      kom_top: [], youth_top: [],
      // elke koers zijn eigen zenders, net als de koers op de tegel
      channels_detail: [{ name: 'NPO 2', time: '15:30', logo: '' }] },
  ],
  last_stage_label: 'Etappe 13 · uitslag',
  last_result: [
    { rank: 1, rider: 'Pogacar Tadej', team: 'UAE', time: '4:12:33' },
    { rank: 2, rider: 'Vingegaard Jonas', team: 'Visma', time: '4:12:47' },
    { rank: 3, rider: 'Evenepoel Remco', team: 'Soudal', time: '4:13:51' },
  ],
  gc_top: [
    { rank: 1, rider: 'Pogacar Tadej', time: '52:14:33', move: 0, gain_s: 0 },
    { rank: 2, rider: 'Vingegaard Jonas', time: '52:16:45', move: 1, gain_s: -14 },
    { rank: 3, rider: 'Evenepoel Remco', time: '52:19:12', move: -1, gain_s: 78 },
  ],
  points_top: [{ rank: 1, rider: 'Philipsen Jasper', team: 'Alpecin-Deceuninck', points: 302, move: 0, gain: 25 }],
  kom_top: [{ rank: 1, rider: 'Ciccone Giulio', team: 'Lidl-Trek', points: 84, move: 2, gain: 10 }],
  youth_top: [{ rank: 1, rider: 'Evenepoel Remco', time: '52:19:12', move: 0, gain_s: 0 }],
  other_label: 'Tour de France Femmes · etappe 3', 
  other_result: [{ rank: 1, rider: 'Vollering Demi', time: '3:02:11' }],
  channels_detail: [
    { name: 'NPO 1', time: '14:15', logo: '' },
    { name: 'Eurosport 1', time: '12:45', logo: '' },
  ],
};

const { races: _races, ...zonderKoerslijst } = attrs;

// een koers die nog moet beginnen: geen uitslag, wel een startlijst. Zo
// levert de sensor het aan (zie `_startlijst_blok`).
const voorDeStart = {
  ...attrs,
  last_stage_label: '', last_result: [], gc_top: [], points_top: [],
  kom_top: [], youth_top: [], other_label: '', other_result: [],
  races: [{ primary: true, key: 'tour-de-france', label: 'Tour de France',
            race_name: 'Tour de France', women: false, level: '1', jersey: '#F3C700' }],
  startlist_riders: 176, startlist_teams: 22,
  startlist_top: [
    { rank: 1, rider: 'Pogacar Tadej', team: 'UAE Team Emirates', team_code: 'UAD', points: 4521 },
    { rank: 2, rider: 'Evenepoel Remco', team: 'Soudal Quick-Step', points: 3310 },
    { rank: 6, rider: 'Vingegaard Jonas', team: 'Team Visma', team_code: 'TVL', points: 2104 },
  ],
};

const gevallen = {
  volledig: attrs,
  'geen profiel': { ...attrs, elevation: [], climbs: [], sprints: [] },
  // een sensor van vóór `races`: de pop-up hoort er hetzelfde uit te zien
  'oude sensor': zonderKoerslijst,
  'voor de start': voorDeStart,
  'alleen tegel': { show_state: 'Morgen', days_until: 1, eyebrow: 'Ronde van Polen', distance_km: 180 },
  leeg: { show_state: 'Klaar' },
};

// per geval: configuratie -> verwacht de kaart zichtbaar te zijn?
const zichtbaarheid = [
  { naam: 'standaard, koers vandaag', config: {}, dagen: 0, zichtbaar: true },
  { naam: 'standaard, koers over 3 dagen', config: {}, dagen: 3, zichtbaar: false },
  { naam: 'binnen 7 dagen, koers over 3', config: { visible_days: 7 }, dagen: 3, zichtbaar: true },
  { naam: 'binnen 7 dagen, koers over 9', config: { visible_days: 7 }, dagen: 9, zichtbaar: false },
  { naam: 'altijd (0), koers over 40', config: { visible_days: 0 }, dagen: 40, zichtbaar: true },
  { naam: 'oude always_show, koers over 40', config: { always_show: true }, dagen: 40, zichtbaar: true },
  { naam: 'aftelweergave zonder grens', config: { view: 'countdown' }, dagen: 40, zichtbaar: true },
];

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const page = await browser.newPage({ viewport: { width: 520, height: 900 } });

const fouten = [];
page.on('pageerror', (e) => fouten.push('pageerror: ' + e.message));
page.on('console', (m) => { if (m.type() === 'error') fouten.push('console: ' + m.text()); });

await page.setContent(`<!doctype html><html><body style="background:#111;margin:0;padding:12px">
  <div id="doel"></div>
  <script>
    // ha-card bestaat alleen in Home Assistant; hier een minimale vervanger.
    customElements.define('ha-card', class extends HTMLElement {
      connectedCallback() { this.style.display='block'; this.style.background='#1c1c1c';
        this.style.borderRadius='16px'; this.style.color='#e8eef4'; }
    });
  </script>
  <script>${fs.readFileSync(KAART, 'utf8')}</script>
</body></html>`);

let mislukt = 0;
for (const [naam, a] of Object.entries(gevallen)) {
  const uitkomst = await page.evaluate(([a]) => {
    document.getElementById('doel').innerHTML = '';
    const kaart = document.createElement('cycling-next-race-card');
    kaart.setConfig({ entity: 'sensor.cycling_next_race' });
    document.getElementById('doel').appendChild(kaart);
    kaart.hass = { states: { 'sensor.cycling_next_race': {
      state: 'Etappe 14', last_updated: String(Math.random()), attributes: a } } };
    const r = kaart.shadowRoot;
    const html = r ? r.innerHTML : '';
    const dlg = r && r.querySelector('dialog');
    if (dlg) dlg.showModal();
    return {
      html_lengte: html.length,
      tekst: r ? r.textContent : '',
      svgs: r ? r.querySelectorAll('svg').length : 0,
      secties: r ? r.querySelectorAll('section').length : 0,
      verborgen: getComputedStyle(kaart).display === 'none',
      nan: /NaN|undefined/.test(html),
      dialoog_open: !!(dlg && dlg.open),
    };
  }, [a]);

  const problemen = [];
  if (uitkomst.nan) problemen.push('NaN of undefined in de uitvoer');
  if (naam === 'leeg' && !uitkomst.verborgen) problemen.push('had zich moeten verbergen');
  if (naam !== 'leeg' && uitkomst.svgs === 0) problemen.push('geen enkele svg getekend');
  if (naam === 'volledig' && uitkomst.secties < 6) problemen.push(`te weinig secties: ${uitkomst.secties}`);
  if (naam === 'voor de start') {
    // de startlijst vult het gat vóór de eerste uitslag
    if (uitkomst.tekst.indexOf('Aan de start') < 0) problemen.push('geen startlijst getekend');
    if (uitkomst.tekst.indexOf('176 renners') < 0) problemen.push('de telling ontbreekt');
    if (uitkomst.tekst.indexOf('(UAD)') < 0) problemen.push('de ploegcode staat niet achter de renner');
    // het cijfer is de plek op de PCS-ranglijst, geen 1-2-3 van onszelf
    if (uitkomst.tekst.indexOf('6Vingegaard') < 0) problemen.push('de ranglijstpositie is hernummerd');
  }
  if (naam === 'volledig' && uitkomst.tekst.indexOf('Aan de start') >= 0)
    problemen.push('startlijst getekend terwijl er een uitslag is');

  if (problemen.length) { console.log(`FOUT  ${naam}: ${problemen.join(', ')}`); mislukt++; }
  else console.log(`ok    ${naam} — ${uitkomst.svgs} svg, ${uitkomst.secties} secties, ${uitkomst.html_lengte} tekens`);

  if (naam === 'volledig') await page.screenshot({ path: 'kaart-volledig.png', fullPage: true });
  if (naam === 'voor de start') await page.screenshot({ path: 'kaart-startlijst.png', fullPage: true });
}

// ── koersen aanklikken in de pop-up ──────────────────────────────
{
  const uit = await page.evaluate(([alle]) => {
    document.getElementById('doel').innerHTML = '';
    const kaart = document.createElement('cycling-next-race-card');
    kaart.setConfig({ entity: 'sensor.cycling_next_race' });
    document.getElementById('doel').appendChild(kaart);
    kaart.hass = { states: { 'sensor.cycling_next_race': {
      state: 'Tour de France', last_updated: 'vast', attributes: alle } } };
    const r = kaart.shadowRoot;
    const dlg = r.querySelector('dialog');
    dlg.showModal();
    const knoppen = r.querySelectorAll('.koers');
    const blokken = r.querySelectorAll('.blok');
    const zichtbaar = () => Array.prototype.map.call(
      blokken, (b) => getComputedStyle(b).display !== 'none');
    const titel = () => r.querySelector('.titel').textContent;

    // de open knop hoort de kleur van de leiderstrui te dragen
    const kleur = (k) => {
      const s = getComputedStyle(k);
      return `${s.backgroundColor}|${s.color}`;
    };

    const start = { open: zichtbaar(), titel: titel(), kleur: kleur(knoppen[0]) };
    if (knoppen.length > 1) knoppen[1].click();
    const na = { open: zichtbaar(), titel: titel(),
                 kleur: knoppen[1] ? kleur(knoppen[1]) : '',
                 dicht: kleur(knoppen[0]),
                 tekst: blokken[1] ? blokken[1].textContent : '' };
    return { knoppen: knoppen.length, blokken: blokken.length, start, na,
             labels: Array.prototype.map.call(knoppen, (k) => k.textContent) };
  }, [attrs]);

  const p = [];
  if (uit.knoppen !== 2) p.push(`${uit.knoppen} koersknoppen, verwacht 2`);
  if (uit.blokken !== 2) p.push(`${uit.blokken} koersblokken, verwacht 2`);
  if (String(uit.start.open) !== 'true,false')
    p.push(`bij openen staat niet alleen de eerste koers open: ${uit.start.open}`);
  if (uit.start.titel !== 'Tour de France')
    p.push(`kop bij openen: "${uit.start.titel}"`);
  if (String(uit.na.open) !== 'false,true')
    p.push(`na de klik staat niet alleen de tweede koers open: ${uit.na.open}`);
  if (uit.na.titel !== 'Tour de France Femmes')
    p.push(`kop na de klik: "${uit.na.titel}"`);
  if (uit.na.tekst.indexOf('Vollering') < 0)
    p.push('de uitslag van de tweede koers staat niet in zijn blok');
  if (uit.na.tekst.indexOf('NPO 2') < 0)
    p.push('de tweede koers toont zijn eigen zenders niet');
  if (uit.na.tekst.indexOf('NPO 1') >= 0)
    p.push('de tweede koers toont de zenders van de tegelkoers');
  if (uit.na.tekst.indexOf('(SDW)') < 0)
    p.push('de ploegcode staat niet achter de renner');
  // het klassement heeft nog geen code: daar hoort de volledige naam te staan
  if (uit.na.tekst.indexOf('(SD Worx)') < 0)
    p.push('zonder ploegcode valt de kaart niet terug op de volledige naam');
  // geel (#F3C700) hoort zwarte letters te krijgen, anders is het onleesbaar
  const GEEL = 'rgb(243, 199, 0)|rgb(14, 21, 32)';
  if (uit.start.kleur !== GEEL)
    p.push(`de open knop draagt de leiderstrui niet: ${uit.start.kleur}`);
  if (uit.na.kleur !== GEEL)
    p.push(`de kleur verhuist niet mee naar de aangeklikte knop: ${uit.na.kleur}`);
  if (uit.na.dicht.indexOf('rgb(243, 199, 0)') === 0)
    p.push('de dichte knop houdt de kleur van de leiderstrui');
  if (p.length) { console.log(`FOUT  koerskeuze: ${p.join(', ')}`); mislukt++; }
  else console.log(`ok    koerskeuze — ${uit.labels.join(' | ')}`);

  await page.screenshot({ path: 'kaart-koerskeuze.png', fullPage: true });
}

// ── vormgeving ───────────────────────────────────────────────────
// Elke vormgeving moet dezelfde kaart opleveren, alleen anders opgemaakt.
// De ha-card-vervanger hierboven zet zijn achtergrond en afronding inline,
// en inline wint van onze stijlen; daarom kijken we naar de binnenmarge.
for (const [design, marge] of [['default', '10px'], ['ha', '8px 16px 16px'],
                               ['bubble', '12px 14px']]) {
  const uit = await page.evaluate(([design, alle]) => {
    document.getElementById('doel').innerHTML = '';
    const kaart = document.createElement('cycling-next-race-card');
    kaart.setConfig({ entity: 'sensor.cycling_next_race', design: design,
                      view: 'countdown', title: 'Wielrennen' });
    document.getElementById('doel').appendChild(kaart);
    kaart.hass = { states: { 'sensor.cycling_next_race': {
      state: 'x', last_updated: design, attributes: alle } } };
    const r = kaart.shadowRoot;
    const el = r.querySelector('ha-card');
    const dlg = r.querySelector('dialog');
    if (dlg) dlg.showModal();
    const kop = r.querySelector('.kaartkop');
    const icoon = r.querySelector('.aftel-icoon');
    // staat het icoon werkelijk midden in zijn rondje? De svg is een
    // blokelement, dus dat gaat niet vanzelf
    const svg = icoon ? icoon.querySelector('svg') : null;
    let scheef = null;
    if (icoon && svg) {
      const a = icoon.getBoundingClientRect();
      const b = svg.getBoundingClientRect();
      scheef = Math.round(Math.abs((b.left + b.width / 2) - (a.left + a.width / 2)));
    }
    return {
      klasse: el.className,
      dialoogklasse: dlg ? dlg.className : '',
      marge: getComputedStyle(el).padding,
      kop: kop ? kop.textContent : '',
      icoonbreedte: icoon ? getComputedStyle(icoon).width : '',
      scheef: scheef,
      svgs: r.querySelectorAll('svg').length,
      nan: /NaN|undefined/.test(r.innerHTML),
    };
  }, [design, attrs]);

  const p = [];
  if (uit.klasse.indexOf(`thema-${design}`) < 0)
    p.push(`ha-card mist de klasse thema-${design}: "${uit.klasse}"`);
  if (uit.dialoogklasse.indexOf(`thema-${design}`) < 0)
    p.push(`het venster mist de klasse thema-${design}: "${uit.dialoogklasse}"`);
  if (uit.marge !== marge) p.push(`binnenmarge ${uit.marge}, verwacht ${marge}`);
  if (uit.kop !== 'Wielrennen') p.push(`de eigen kop ontbreekt: "${uit.kop}"`);
  if (uit.nan) p.push('NaN of undefined');
  if (design === 'bubble' && uit.icoonbreedte !== '38px')
    p.push(`het icoon staat niet in een rondje (breedte ${uit.icoonbreedte})`);
  if (design === 'bubble' && uit.scheef !== 0)
    p.push(`het icoon staat ${uit.scheef}px uit het midden van zijn rondje`);
  if (p.length) { console.log(`FOUT  vormgeving ${design}: ${p.join(', ')}`); mislukt++; }
  else console.log(`ok    vormgeving ${design} — marge ${uit.marge}, ${uit.svgs} svg`);

  await page.screenshot({ path: `kaart-design-${design}.png` });
}

// ── onderdelen van het detailvenster ─────────────────────────────
{
  const uit = await page.evaluate(([alle]) => {
    const venster = (sections) => {
      document.getElementById('doel').innerHTML = '';
      const kaart = document.createElement('cycling-next-race-card');
      const config = { entity: 'sensor.cycling_next_race' };
      if (sections) config.sections = sections;
      kaart.setConfig(config);
      document.getElementById('doel').appendChild(kaart);
      kaart.hass = { states: { 'sensor.cycling_next_race': {
        state: 'x', last_updated: String(sections), attributes: alle } } };
      const r = kaart.shadowRoot;
      return {
        tekst: r.querySelector('dialog').textContent,
        secties: r.querySelectorAll('section').length,
        profielen: r.querySelectorAll('dialog svg').length,
      };
    };
    return {
      alles: venster(null),
      twee: venster(['result', 'gc']),
      leeg: venster([]),
      // zonder profiel wordt de eerste etappe van een pop-upkoers nergens
      // getekend; die hoort dan bij "Komende dagen" te staan
      komend: venster(['upcoming']),
    };
  }, [attrs]);

  const p = [];
  if (uit.alles.tekst.indexOf('Bergklassement') < 0)
    p.push('zonder keuze staat niet alles in het venster');
  if (uit.twee.tekst.indexOf('Algemeen klassement') < 0)
    p.push('een gekozen onderdeel ontbreekt');
  if (uit.twee.tekst.indexOf('Bergklassement') >= 0)
    p.push('een niet gekozen onderdeel staat er toch in');
  if (uit.twee.tekst.indexOf('Komende dagen') >= 0)
    p.push('"Komende dagen" staat er ondanks de keuze');
  if (uit.twee.profielen !== 0)
    p.push(`${uit.twee.profielen} profielen terwijl het profiel niet gekozen is`);
  if (uit.leeg.secties !== uit.alles.secties)
    p.push('een lege keuze levert niet hetzelfde op als geen keuze');
  if (uit.komend.tekst.indexOf('Etappe 4 · Tour de France Femmes') < 0)
    p.push('zonder profiel valt de eerste etappe van een pop-upkoers weg');
  if (p.length) { console.log(`FOUT  onderdelen: ${p.join(', ')}`); mislukt++; }
  else console.log(`ok    onderdelen — alles ${uit.alles.secties} secties, keuze ${uit.twee.secties}`);
}

// ── niveaus per kaart ────────────────────────────────────────────
/* Twee kaarten op hetzelfde dashboard met een andere niveaukeuze. De
 * tegelkoers van de sensor is de mannen-WorldTour; een kaart die alleen de
 * vrouwen wil hoort de vrouwenkoers naar de tegel te halen in plaats van
 * leeg te blijven. */
{
  const uit = await page.evaluate(([alle]) => {
    const bouw = (levels, preview) => {
      document.getElementById('doel').innerHTML = '';
      const kaart = document.createElement('cycling-next-race-card');
      const config = { entity: 'sensor.cycling_next_race', visible_days: 0 };
      if (levels) config.levels = levels;
      kaart.setConfig(config);
      if (preview) kaart.preview = true;
      document.getElementById('doel').appendChild(kaart);
      kaart.hass = { states: { 'sensor.cycling_next_race': {
        state: 'x', last_updated: String(levels) + preview, attributes: alle } } };
      const r = kaart.shadowRoot;
      const dlg = r.querySelector('dialog');
      const html = r.innerHTML;
      return {
        verborgen: getComputedStyle(kaart).display === 'none',
        tegel: (r.querySelector('ha-card') || {}).textContent || '',
        knoppen: r.querySelectorAll('.koers').length,
        titel: dlg ? dlg.querySelector('.titel').textContent : '',
        venster: dlg ? dlg.textContent : '',
        nan: /NaN|undefined/.test(html),
      };
    };
    return {
      alles: bouw(null, false),
      mannen: bouw(['1'], false),
      vrouwen: bouw(['24'], false),
      niets: bouw(['26'], false),
      nietsPreview: bouw(['26'], true),
    };
  }, [attrs]);

  const p = [];
  if (uit.alles.knoppen !== 2) p.push(`zonder keuze ${uit.alles.knoppen} knoppen i.p.v. 2`);
  // alleen de mannen: geen tweede koers meer, en ook geen vrouwenetappe
  // onder "Komende dagen"
  if (uit.mannen.knoppen !== 0)
    p.push(`bij één niveau blijven er ${uit.mannen.knoppen} koersknoppen staan`);
  if (uit.mannen.titel !== 'Tour de France')
    p.push(`verkeerde koers bij alleen de mannen: ${uit.mannen.titel}`);
  if (uit.mannen.venster.indexOf('Femmes') >= 0)
    p.push('een vrouwenetappe blijft in het venster staan');
  if (uit.mannen.venster.indexOf('Etappe 15 · Tour de France') < 0)
    p.push('de eigen komende etappe is verdwenen');
  // alleen de vrouwen: de vrouwenkoers komt op de tegel
  if (uit.vrouwen.titel !== 'Tour de France Femmes')
    p.push(`de vrouwenkoers komt niet op de tegel: ${uit.vrouwen.titel}`);
  if (uit.vrouwen.tegel.indexOf('Etappe 4 · Tour de France Femmes') < 0)
    p.push(`verkeerde etappe op de tegel: ${uit.vrouwen.tegel}`);
  if (uit.vrouwen.venster.indexOf('Pogacar') >= 0)
    p.push('de mannenuitslag staat nog in het venster');
  if (uit.vrouwen.venster.indexOf('Vollering') < 0)
    p.push('de vrouwenuitslag ontbreekt');
  if (uit.vrouwen.nan) p.push('NaN of undefined bij de gepromoveerde koers');
  // een niveau zonder koers: verbergen, behalve in het bewerkscherm
  if (!uit.niets.verborgen) p.push('een niveau zonder koers verbergt de kaart niet');
  if (uit.nietsPreview.verborgen) p.push('in het bewerkscherm hoort de kaart te blijven staan');
  if (uit.nietsPreview.tegel.indexOf('Geen koers') < 0)
    p.push(`geen melding in het bewerkscherm: ${uit.nietsPreview.tegel}`);

  if (p.length) { console.log(`FOUT  niveaus: ${p.join(', ')}`); mislukt++; }
  else console.log('ok    niveaus — mannen, vrouwen en een leeg niveau elk goed');
}

// ── preview-modus: nooit verbergen ───────────────────────────────
{
  const uit = await page.evaluate(([alle]) => {
    const maak = (preview) => {
      document.getElementById('doel').innerHTML = '';
      const kaart = document.createElement('cycling-next-race-card');
      kaart.setConfig({ entity: 'sensor.cycling_next_race', visible_days: 2 });
      document.getElementById('doel').appendChild(kaart);
      // hass eerst, preview daarna: de vololgorde die Home Assistant kan aanhouden
      kaart.hass = { states: { 'sensor.cycling_next_race': {
        state: 'x', last_updated: 'vast',
        attributes: { ...alle, days_until: 30, show_state: 'Gepland' } } } };
      if (preview) kaart.preview = true;
      return { zichtbaar: getComputedStyle(kaart).display !== 'none',
               inhoud: kaart.shadowRoot.innerHTML.length };
    };
    return { zonder: maak(false), met: maak(true) };
  }, [attrs]);

  const p = [];
  if (uit.zonder.zichtbaar) p.push('buiten de bewerkmodus had hij zich moeten verbergen');
  if (!uit.met.zichtbaar) p.push('in de bewerkmodus blijft hij verborgen en is dan niet aanklikbaar');
  if (uit.met.inhoud === 0) p.push('in de bewerkmodus wordt niets getekend');
  if (p.length) { console.log(`FOUT  preview-modus: ${p.join(', ')}`); mislukt++; }
  else console.log('ok    preview-modus — verborgen op het dashboard, zichtbaar in het bewerkscherm');
}

// ── entiteit verdwijnt nadat de kaart zich verborgen heeft ───────
{
  const uit = await page.evaluate(([alle]) => {
    document.getElementById('doel').innerHTML = '';
    const kaart = document.createElement('cycling-next-race-card');
    kaart.setConfig({ entity: 'sensor.cycling_next_race', visible_days: 2 });
    document.getElementById('doel').appendChild(kaart);
    // koers ver weg: de kaart verbergt zichzelf
    kaart.hass = { states: { 'sensor.cycling_next_race': {
      state: 'x', last_updated: 'een',
      attributes: { ...alle, days_until: 30, show_state: 'Gepland' } } } };
    const verborgen = getComputedStyle(kaart).display === 'none';
    // en daarna is de sensor er niet meer, bijvoorbeeld na hernoemen
    kaart.hass = { states: {} };
    return {
      verborgen,
      zichtbaar: getComputedStyle(kaart).display !== 'none',
      melding: kaart.shadowRoot.textContent.indexOf('bestaat niet') >= 0,
    };
  }, [attrs]);

  const p = [];
  if (!uit.verborgen) p.push('de kaart verborg zich niet bij een koers ver weg');
  if (!uit.zichtbaar) p.push('de melding blijft onzichtbaar op een kaart die zich verborgen had');
  if (!uit.melding) p.push('er staat geen melding over de ontbrekende sensor');
  if (p.length) { console.log(`FOUT  sensor verdwijnt: ${p.join(', ')}`); mislukt++; }
  else console.log('ok    sensor verdwijnt — de kaart komt terug in beeld met een melding');
}

// ── sensor niet beschikbaar ──────────────────────────────────────
// Zonder attributen tekent de tegel "1 km" met "Profiel nog niet bekend"
// eronder: dat ziet eruit als een koers waarvan het profiel ontbreekt,
// terwijl er niets is opgehaald.
{
  const uit = await page.evaluate(() => {
    const maak = (state) => {
      document.getElementById('doel').innerHTML = '';
      const kaart = document.createElement('cycling-next-race-card');
      kaart.setConfig({ entity: 'sensor.cycling_next_race' });
      document.getElementById('doel').appendChild(kaart);
      kaart.hass = { states: { 'sensor.cycling_next_race': {
        state, last_updated: state, attributes: {} } } };
      return kaart;
    };
    const weg = maak('unavailable');
    const onbekend = maak('unknown');
    return {
      zichtbaar: getComputedStyle(weg).display !== 'none',
      melding: weg.shadowRoot.textContent.indexOf('niet beschikbaar') >= 0,
      geenNepkoers: weg.shadowRoot.textContent.indexOf('1 km') < 0,
      onbekend: onbekend.shadowRoot.textContent.indexOf('nog onbekend') >= 0,
    };
  });

  const p = [];
  if (!uit.zichtbaar) p.push('de kaart verbergt zich in plaats van te melden');
  if (!uit.melding) p.push('geen melding bij unavailable');
  if (!uit.geenNepkoers) p.push('er staat nog een koers van 1 km');
  if (!uit.onbekend) p.push('geen melding bij unknown');
  if (p.length) { console.log(`FOUT  sensor onbeschikbaar: ${p.join(', ')}`); mislukt++; }
  else console.log('ok    sensor onbeschikbaar — melding in plaats van een lege tegel');
}

// ── zichtbaarheid en aftelweergave ───────────────────────────────
for (const geval of zichtbaarheid) {
  const uit = await page.evaluate(([config, dagen, alle]) => {
    document.getElementById('doel').innerHTML = '';
    const kaart = document.createElement('cycling-next-race-card');
    kaart.setConfig({ entity: 'sensor.cycling_next_race', ...config });
    document.getElementById('doel').appendChild(kaart);
    kaart.hass = { states: { 'sensor.cycling_next_race': {
      state: 'x', last_updated: String(Math.random()),
      attributes: { ...alle, days_until: dagen, show_state: dagen === 0 ? 'Vandaag' : 'Gepland',
        countdown: dagen === 0 ? '🟢 Vandaag' : `Over ${dagen} dagen` } } } };
    const r = kaart.shadowRoot;
    return {
      zichtbaar: getComputedStyle(kaart).display !== 'none',
      aftel: !!(r && r.querySelector('.aftel')),
      wanneer: r && r.querySelector('.aftel-wanneer') ? r.querySelector('.aftel-wanneer').textContent.trim() : '',
      nan: /NaN|undefined/.test(r ? r.innerHTML : ''),
    };
  }, [geval.config, geval.dagen, attrs]);

  const p = [];
  if (uit.zichtbaar !== geval.zichtbaar)
    p.push(`zichtbaar=${uit.zichtbaar}, verwacht ${geval.zichtbaar}`);
  if (uit.nan) p.push('NaN of undefined');
  if (geval.config.view === 'countdown') {
    if (!uit.aftel) p.push('geen aftelregel getekend');
    if (!uit.wanneer) p.push('aftelregel zonder tekst');
  }
  if (p.length) { console.log(`FOUT  ${geval.naam}: ${p.join(', ')}`); mislukt++; }
  else console.log(`ok    ${geval.naam}${uit.wanneer ? ' — "' + uit.wanneer + '"' : ''}`);

  if (geval.config.view === 'countdown') await page.screenshot({ path: 'kaart-aftellen.png' });
}

if (fouten.length) { console.log('\nJS-fouten in de pagina:'); fouten.forEach((f) => console.log('  ' + f)); mislukt++; }
await browser.close();
process.exit(mislukt ? 1 : 0);
