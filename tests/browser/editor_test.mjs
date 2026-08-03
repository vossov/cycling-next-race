/*
 * Test de visuele editor van de kaart in Chromium.
 *
 * Twee paden: met ha-form (zoals in Home Assistant, hier nagebootst) en de
 * terugval zonder. Beide moeten dezelfde velden aanbieden en bij wijziging
 * een config-changed sturen met de volledige configuratie.
 *
 *   npm install playwright
 *   node tests/browser/editor_test.mjs
 */
import { chromium } from 'playwright';
import fs from 'fs';

const KAART = new URL('../../custom_components/cycling_next_race/www/cycling-next-race-card.js', import.meta.url).pathname;
const CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';

const browser = await chromium.launch({ executablePath: CHROME });
let mislukt = 0;

for (const metHaForm of [false, true]) {
  const page = await browser.newPage();
  const fouten = [];
  page.on('pageerror', (e) => fouten.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') fouten.push(m.text()); });

  const haFormStub = metHaForm ? `
    customElements.define('ha-form', class extends HTMLElement {
      set schema(v) { this._schema = v; this.render(); }
      set data(v) { this._data = v; }
      render() {
        this.innerHTML = (this._schema || []).map(s => '<div class="veld">' + s.name + '</div>').join('');
      }
    });` : '';

  await page.setContent(`<!doctype html><html><body>
    <div id="doel"></div>
    <script>
      customElements.define('ha-card', class extends HTMLElement {});
      ${haFormStub}
    </script>
    <script>${fs.readFileSync(KAART, 'utf8')}</script>
  </body></html>`);

  const uit = await page.evaluate(() => {
    const Kaart = customElements.get('cycling-next-race-card');
    const editor = Kaart.getConfigElement();
    if (!editor || editor.constructor === HTMLElement) return { bestaat: false };

    document.getElementById('doel').appendChild(editor);
    editor.hass = { states: {} };
    editor.setConfig({ entity: 'sensor.cycling_next_race' });

    const gewijzigd = [];
    editor.addEventListener('config-changed', (e) => gewijzigd.push(e.detail.config));

    const r = editor.shadowRoot;
    const viaHaForm = !!r.querySelector('ha-form');
    let velden;
    if (viaHaForm) {
      velden = (r.querySelector('ha-form')._schema || []).map((s) => s.name);
      // bootst na wat ha-form doet als de gebruiker iets aanpast
      r.querySelector('ha-form').dispatchEvent(new CustomEvent('value-changed', {
        detail: { value: { entity: 'sensor.cycling_next_race', details: false, always_show: true } },
      }));
    } else {
      velden = [...r.querySelectorAll('[name]')].map((el) => el.getAttribute('name'));
      const vinkje = r.querySelector('[name="always_show"]');
      vinkje.checked = true;
      vinkje.dispatchEvent(new Event('change', { bubbles: true }));
    }

    return {
      bestaat: true, viaHaForm, velden,
      events: gewijzigd.length,
      laatste: gewijzigd[gewijzigd.length - 1] || null,
      stub: Kaart.getStubConfig(),
    };
  });

  const naam = metHaForm ? 'met ha-form' : 'terugval zonder ha-form';
  const problemen = [];
  if (!uit.bestaat) problemen.push('getConfigElement levert geen editor');
  else {
    const verwacht = ['entity', 'details', 'always_show'];
    if (JSON.stringify(uit.velden) !== JSON.stringify(verwacht))
      problemen.push(`velden ${JSON.stringify(uit.velden)} i.p.v. ${JSON.stringify(verwacht)}`);
    if (uit.viaHaForm !== metHaForm) problemen.push(`verkeerde weg gekozen (ha-form=${uit.viaHaForm})`);
    if (uit.events !== 1) problemen.push(`${uit.events} config-changed events`);
    if (!uit.laatste || uit.laatste.type !== 'custom:cycling-next-race-card')
      problemen.push('type ontbreekt in de doorgegeven configuratie');
    if (uit.laatste && uit.laatste.always_show !== true)
      problemen.push('de wijziging kwam niet door');
    for (const s of verwacht) if (!(s in uit.stub)) problemen.push(`getStubConfig mist ${s}`);
  }
  if (fouten.length) problemen.push('JS-fouten: ' + fouten.join(' | '));

  if (problemen.length) { console.log(`FOUT  ${naam}: ${problemen.join(', ')}`); mislukt++; }
  else console.log(`ok    ${naam} — velden ${uit.velden.join(', ')}, config-changed verstuurd`);

  await page.close();
}

await browser.close();
process.exit(mislukt ? 1 : 0);
