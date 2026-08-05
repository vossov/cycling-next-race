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
      race_key: 'tour-de-france',
      departure: 'Loudenvielle', arrival: 'Plateau de Beille', distance_km: 197,
      vertical_m: 2400, profile_score: 402, watchability: 8 },
    { date: '2026-07-19', eyebrow: 'Etappe 4 · Tour de France Femmes · Dames', show_state: 'Overmorgen',
      race_key: 'tour-de-france-femmes',
      departure: 'Saumur', arrival: 'Poitiers', distance_km: 130, vertical_m: 1500,
      profile_score: 120, watchability: 5 },
    { date: '2026-07-20', eyebrow: 'Etappe 5 · Tour de France Femmes · Dames', show_state: 'Za 20 jul',
      race_key: 'tour-de-france-femmes',
      departure: 'Poitiers', arrival: 'Limoges', distance_km: 152, vertical_m: 1900,
      profile_score: 180, watchability: 6 },
  ],
  // zoals _races_block ze zet: de tegelkoers eerst (primary), daarna de
  // koersen die tegelijk lopen met hun eigen uitslag en standen
  races: [
    { primary: true, key: 'tour-de-france', label: 'Tour de France',
      race_name: 'Tour de France', women: false, jersey: '#F3C700' },
    { key: 'tour-de-france-femmes', label: 'Tour de France Femmes · Dames',
      race_name: 'Tour de France Femmes', women: true, jersey: '#F3C700',
      eyebrow: 'Etappe 4 · Tour de France Femmes · Dames', show_state: 'Overmorgen',
      last_stage_label: 'Etappe 3 · Tour de France Femmes',
      last_result: [
        { rank: 1, rider: 'Vollering Demi', team: 'FDJ', time: '3:02:11' },
        { rank: 2, rider: 'Kopecky Lotte', team: 'SD Worx', time: '3:02:11' },
      ],
      gc_top: [
        { rank: 1, rider: 'Vollering Demi', time: '9:14:02', move: 1, gain_s: -22 },
        { rank: 2, rider: 'Kopecky Lotte', time: '9:14:36', move: -1, gain_s: 22 },
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
  points_top: [{ rank: 1, rider: 'Philipsen Jasper', points: 302, move: 0, gain: 25 }],
  kom_top: [{ rank: 1, rider: 'Ciccone Giulio', points: 84, move: 2, gain: 10 }],
  youth_top: [{ rank: 1, rider: 'Evenepoel Remco', time: '52:19:12', move: 0, gain_s: 0 }],
  other_label: 'Tour de France Femmes · etappe 3', 
  other_result: [{ rank: 1, rider: 'Vollering Demi', time: '3:02:11' }],
  channels_detail: [
    { name: 'NPO 1', time: '14:15', logo: '' },
    { name: 'Eurosport 1', time: '12:45', logo: '' },
  ],
};

const { races: _races, ...zonderKoerslijst } = attrs;

const gevallen = {
  volledig: attrs,
  'geen profiel': { ...attrs, elevation: [], climbs: [], sprints: [] },
  // een sensor van vóór `races`: de pop-up hoort er hetzelfde uit te zien
  'oude sensor': zonderKoerslijst,
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

  if (problemen.length) { console.log(`FOUT  ${naam}: ${problemen.join(', ')}`); mislukt++; }
  else console.log(`ok    ${naam} — ${uitkomst.svgs} svg, ${uitkomst.secties} secties, ${uitkomst.html_lengte} tekens`);

  if (naam === 'volledig') await page.screenshot({ path: 'kaart-volledig.png', fullPage: true });
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
