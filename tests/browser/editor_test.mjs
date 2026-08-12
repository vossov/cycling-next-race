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

// De onderdelen van het detailvenster, in de volgorde waarin de kaart ze
// zet. Hier met opzet uitgeschreven: een wijziging in de kaart hoort hier
// zichtbaar te worden en niet stilzwijgend mee te bewegen.
const SECTIES = ['profile', 'tv', 'upcoming', 'result', 'gc', 'points', 'kom', 'youth'];

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
    let sectiekeuzes = null;
    if (viaHaForm) {
      velden = (r.querySelector('ha-form')._schema || []).map((s) => s.name);
      // bootst na wat ha-form doet als de gebruiker iets aanpast
      r.querySelector('ha-form').dispatchEvent(new CustomEvent('value-changed', {
        detail: { value: { entity: 'sensor.cycling_next_race', view: 'countdown',
                           design: 'bubble', visible_days: 7, details: false,
                           sections: ['result', 'gc'], title: 'Wielrennen' } },
      }));
    } else {
      // de sectievakjes delen één naam, zoals een checkboxgroep hoort;
      // voor de vergelijking tellen ze daarom als één veld
      velden = [...new Set([...r.querySelectorAll('[name]')]
        .map((el) => el.getAttribute('name')))];
      sectiekeuzes = r.querySelectorAll('[name="sections"]').length;
      r.querySelector('[name="design"]').value = 'bubble';
      r.querySelector('[name="title"]').value = 'Wielrennen';
      // alles op twee na uitvinken moet als keuze doorkomen, in de vaste
      // volgorde van de vakjes en niet in die van het aanvinken
      const vakjes = [...r.querySelectorAll('[name="sections"]')];
      vakjes.forEach((v) => { v.checked = v.value === 'result' || v.value === 'gc'; });
      const dagen = r.querySelector('[name="visible_days"]');
      dagen.value = '7';
      dagen.dispatchEvent(new Event('change', { bubbles: true }));
    }

    return {
      bestaat: true, viaHaForm, velden, sectiekeuzes,
      events: gewijzigd.length,
      laatste: gewijzigd[gewijzigd.length - 1] || null,
      stub: Kaart.getStubConfig(),
      // een kaart die met de stub begint hoort alle onderdelen te tonen
      stubGevuld: (() => {
        const k = document.createElement('cycling-next-race-card');
        k.setConfig(Kaart.getStubConfig());
        return { sections: k._config.sections };
      })(),
      // alles aangevinkt en een lege kop horen niet in de opgeslagen
      // configuratie te belanden: dat is hetzelfde als ze weglaten
      allesAan: (() => {
        const e3 = Kaart.getConfigElement();
        e3.setConfig({ entity: 'sensor.cycling_next_race' });
        let doorgegeven = null;
        e3.addEventListener('config-changed', (e) => { doorgegeven = e.detail.config; });
        e3._wijzig({
          type: 'custom:cycling-next-race-card',
          entity: 'sensor.cycling_next_race', view: 'profile', design: 'default',
          visible_days: 2, details: true,
          sections: ['profile', 'tv', 'upcoming', 'result', 'gc', 'points', 'kom', 'youth'],
          title: '',
        });
        return doorgegeven || {};
      })(),
      // onzin in de configuratie mag niet blijven staan
      opgeschoond: (() => {
        const e2 = Kaart.getConfigElement();
        e2.setConfig({ design: 'bestaat-niet', sections: ['gc', 'onzin'] });
        return { design: e2._config.design, sections: e2._config.sections };
      })(),
    };
  });

  const naam = metHaForm ? 'met ha-form' : 'terugval zonder ha-form';
  const problemen = [];
  if (!uit.bestaat) problemen.push('getConfigElement levert geen editor');
  else {
    const verwacht = ['entity', 'view', 'design', 'visible_days', 'details',
                      'sections', 'title'];
    if (JSON.stringify(uit.velden) !== JSON.stringify(verwacht))
      problemen.push(`velden ${JSON.stringify(uit.velden)} i.p.v. ${JSON.stringify(verwacht)}`);
    if (uit.viaHaForm !== metHaForm) problemen.push(`verkeerde weg gekozen (ha-form=${uit.viaHaForm})`);
    if (uit.events !== 1) problemen.push(`${uit.events} config-changed events`);
    if (!uit.laatste || uit.laatste.type !== 'custom:cycling-next-race-card')
      problemen.push('type ontbreekt in de doorgegeven configuratie');
    if (uit.laatste && uit.laatste.visible_days !== 7)
      problemen.push(`de wijziging kwam niet door (visible_days=${uit.laatste && uit.laatste.visible_days})`);
    if (uit.laatste && uit.laatste.design !== 'bubble')
      problemen.push(`vormgeving kwam niet door (design=${uit.laatste && uit.laatste.design})`);
    if (uit.laatste && uit.laatste.title !== 'Wielrennen')
      problemen.push(`kop kwam niet door (title=${uit.laatste && uit.laatste.title})`);
    if (!uit.laatste || String(uit.laatste.sections) !== 'result,gc')
      problemen.push(`sectiekeuze kwam niet door (sections=${uit.laatste && uit.laatste.sections})`);
    if (!metHaForm && uit.sectiekeuzes !== 8)
      problemen.push(`${uit.sectiekeuzes} sectievakjes, verwacht 8`);
    // sections en title horen niet in de stub: weglaten betekent "alles"
    // respectievelijk "geen kop", en dat moet zo blijven als er later een
    // onderdeel bijkomt
    const inStub = ['entity', 'view', 'design', 'visible_days', 'details'];
    for (const s of inStub) if (!(s in uit.stub)) problemen.push(`getStubConfig mist ${s}`);
    for (const s of ['sections', 'title'])
      if (s in uit.stub) problemen.push(`getStubConfig zet ${s} vast`);
    if (String(uit.stubGevuld.sections) !== SECTIES.join(','))
      problemen.push(`een kaart uit de stub toont niet alles: ${uit.stubGevuld.sections}`);
    if (uit.allesAan.sections !== undefined)
      problemen.push('alles aangevinkt komt als lijst in de configuratie terecht');
    if (uit.allesAan.title !== undefined)
      problemen.push('een lege kop komt in de configuratie terecht');
    if (uit.opgeschoond.design !== 'default')
      problemen.push(`onbekende vormgeving blijft staan: ${uit.opgeschoond.design}`);
    if (String(uit.opgeschoond.sections) !== 'gc')
      problemen.push(`onbekende sectie blijft staan: ${uit.opgeschoond.sections}`);
  }
  if (fouten.length) problemen.push('JS-fouten: ' + fouten.join(' | '));

  if (problemen.length) { console.log(`FOUT  ${naam}: ${problemen.join(', ')}`); mislukt++; }
  else console.log(`ok    ${naam} — velden ${uit.velden.join(', ')}, config-changed verstuurd`);

  await page.close();
}

await browser.close();
process.exit(mislukt ? 1 : 0);
