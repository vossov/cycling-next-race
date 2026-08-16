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

// De niveaus die de kaart aanbiedt, gelijk aan NIVEAUS in const.py. Ook hier
// met opzet uitgeschreven; tests/test_kaart.py bewaakt de Python-kant.
const NIVEAUS = ['1', '24', '26', '27'];

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
    let niveaukeuzes = null;
    if (viaHaForm) {
      velden = (r.querySelector('ha-form')._schema || []).map((s) => s.name);
      // bootst na wat ha-form doet als de gebruiker iets aanpast
      r.querySelector('ha-form').dispatchEvent(new CustomEvent('value-changed', {
        detail: { value: { entity: 'sensor.cycling_next_race', view: 'countdown',
                           design: 'bubble', visible_days: 7, details: false,
                           sections: ['result', 'gc'], levels: ['24'],
                           title: 'Wielrennen' } },
      }));
    } else {
      // de sectievakjes delen één naam, zoals een checkboxgroep hoort;
      // voor de vergelijking tellen ze daarom als één veld
      velden = [...new Set([...r.querySelectorAll('[name]')]
        .map((el) => el.getAttribute('name')))];
      sectiekeuzes = r.querySelectorAll('[name="sections"]').length;
      niveaukeuzes = r.querySelectorAll('[name="levels"]').length;
      r.querySelector('[name="design"]').value = 'bubble';
      r.querySelector('[name="title"]').value = 'Wielrennen';
      // alles op twee na uitvinken moet als keuze doorkomen, in de vaste
      // volgorde van de vakjes en niet in die van het aanvinken
      const vakjes = [...r.querySelectorAll('[name="sections"]')];
      vakjes.forEach((v) => { v.checked = v.value === 'result' || v.value === 'gc'; });
      const niveaus = [...r.querySelectorAll('[name="levels"]')];
      niveaus.forEach((v) => { v.checked = v.value === '24'; });
      const dagen = r.querySelector('[name="visible_days"]');
      dagen.value = '7';
      dagen.dispatchEvent(new Event('change', { bubbles: true }));
    }

    const voet = r.querySelector('.versie');
    return {
      bestaat: true, viaHaForm, velden, sectiekeuzes, niveaukeuzes,
      // de versie van de kaart hoort in het bewerkscherm te staan; anders
      // is alleen die van de Python-kant te zien
      voetregel: voet ? voet.textContent : '',
      voetzichtbaar: voet ? getComputedStyle(voet).fontSize : '',
      events: gewijzigd.length,
      laatste: gewijzigd[gewijzigd.length - 1] || null,
      stub: Kaart.getStubConfig(),
      // een tweede setConfig moet in het formulier terechtkomen; anders
      // blijft het staan op de configuratie van de eerste keer
      tweedeSetConfig: (() => {
        const e4 = Kaart.getConfigElement();
        document.getElementById('doel').appendChild(e4);
        e4.hass = { states: {} };
        e4.setConfig({ entity: 'sensor.cycling_next_race', view: 'profile' });
        e4.setConfig({ entity: 'sensor.cycling_next_race', view: 'countdown',
                       design: 'bubble' });
        const f = e4.shadowRoot.querySelector('ha-form');
        if (f) return { via: 'ha-form', view: (f._data || {}).view,
                        design: (f._data || {}).design };
        const s = e4.shadowRoot.querySelector('[name="view"]');
        return { via: 'terugval', view: s ? s.value : '',
                 design: e4.shadowRoot.querySelector('[name="design"]').value };
      })(),
      // een kaart die met de stub begint hoort alle onderdelen te tonen
      stubGevuld: (() => {
        const k = document.createElement('cycling-next-race-card');
        k.setConfig(Kaart.getStubConfig());
        return { sections: k._config.sections, levels: k._config.levels };
      })(),
      // alles aangevinkt en een lege kop horen niet in de opgeslagen
      // configuratie te belanden: dat is hetzelfde als ze weglaten. Maar de
      // editor moet er daarna zélf nog mee kunnen tekenen — een sleutel die
      // alleen uit de doorgegeven configuratie verdwijnt mag niet ook uit
      // zijn eigen state verdwijnen
      allesAan: (() => {
        const e3 = Kaart.getConfigElement();
        document.getElementById('doel').appendChild(e3);
        e3.setConfig({ entity: 'sensor.cycling_next_race' });
        let doorgegeven = null;
        e3.addEventListener('config-changed', (e) => { doorgegeven = e.detail.config; });
        e3._wijzig({
          type: 'custom:cycling-next-race-card',
          entity: 'sensor.cycling_next_race', view: 'profile', design: 'default',
          visible_days: 2, details: true,
          sections: ['profile', 'tv', 'upcoming', 'result', 'gc', 'points', 'kom', 'youth'],
          levels: ['1', '24', '26', '27'],
          title: '',
        });
        let opnieuw = 'ok';
        try {
          e3.hass = { states: {} };
        } catch (err) {
          opnieuw = err.message;
        }
        return { ...(doorgegeven || {}), _opnieuw: opnieuw };
      })(),
      // onzin in de configuratie mag niet blijven staan
      opgeschoond: (() => {
        const e2 = Kaart.getConfigElement();
        e2.setConfig({ design: 'bestaat-niet', sections: ['gc', 'onzin'],
                       levels: ['24', '999'] });
        return { design: e2._config.design, sections: e2._config.sections,
                 levels: e2._config.levels };
      })(),
    };
  });

  const naam = metHaForm ? 'met ha-form' : 'terugval zonder ha-form';
  const problemen = [];
  if (!uit.bestaat) problemen.push('getConfigElement levert geen editor');
  else {
    const verwacht = ['entity', 'view', 'design', 'visible_days', 'details',
                      'sections', 'levels', 'title'];
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
    if (!uit.laatste || String(uit.laatste.levels) !== '24')
      problemen.push(`niveaukeuze kwam niet door (levels=${uit.laatste && uit.laatste.levels})`);
    if (!metHaForm && uit.niveaukeuzes !== NIVEAUS.length)
      problemen.push(`${uit.niveaukeuzes} niveauvakjes, verwacht ${NIVEAUS.length}`);
    // sections en title horen niet in de stub: weglaten betekent "alles"
    // respectievelijk "geen kop", en dat moet zo blijven als er later een
    // onderdeel bijkomt
    const inStub = ['entity', 'view', 'design', 'visible_days', 'details'];
    for (const s of inStub) if (!(s in uit.stub)) problemen.push(`getStubConfig mist ${s}`);
    for (const s of ['sections', 'levels', 'title'])
      if (s in uit.stub) problemen.push(`getStubConfig zet ${s} vast`);
    if (String(uit.stubGevuld.sections) !== SECTIES.join(','))
      problemen.push(`een kaart uit de stub toont niet alles: ${uit.stubGevuld.sections}`);
    if (String(uit.stubGevuld.levels) !== NIVEAUS.join(','))
      problemen.push(`een kaart uit de stub mist niveaus: ${uit.stubGevuld.levels}`);
    if (uit.allesAan.sections !== undefined)
      problemen.push('alles aangevinkt komt als lijst in de configuratie terecht');
    if (uit.allesAan.levels !== undefined)
      problemen.push('alle niveaus aangevinkt komt als lijst in de configuratie terecht');
    if (uit.allesAan.title !== undefined)
      problemen.push('een lege kop komt in de configuratie terecht');
    if (uit.allesAan._opnieuw !== 'ok')
      problemen.push(`tekent niet opnieuw na een wijziging: ${uit.allesAan._opnieuw}`);
    if (!/^Cycling Next Race-kaart \d+\.\d+\.\d+$/.test(uit.voetregel))
      problemen.push(`geen versie in het bewerkscherm: "${uit.voetregel}"`);
    if (uit.voetzichtbaar !== '11px')
      problemen.push(`de versieregel krijgt geen opmaak (${uit.voetzichtbaar})`);
    if (uit.tweedeSetConfig.view !== 'countdown' || uit.tweedeSetConfig.design !== 'bubble')
      problemen.push(
        `een tweede setConfig komt niet in het formulier: ${JSON.stringify(uit.tweedeSetConfig)}`
      );
    if (uit.opgeschoond.design !== 'default')
      problemen.push(`onbekende vormgeving blijft staan: ${uit.opgeschoond.design}`);
    if (String(uit.opgeschoond.sections) !== 'gc')
      problemen.push(`onbekende sectie blijft staan: ${uit.opgeschoond.sections}`);
    if (String(uit.opgeschoond.levels) !== '24')
      problemen.push(`onbekend niveau blijft staan: ${uit.opgeschoond.levels}`);
  }
  if (fouten.length) problemen.push('JS-fouten: ' + fouten.join(' | '));

  if (problemen.length) { console.log(`FOUT  ${naam}: ${problemen.join(', ')}`); mislukt++; }
  else console.log(`ok    ${naam} — velden ${uit.velden.join(', ')}, config-changed verstuurd`);

  await page.close();
}

await browser.close();
process.exit(mislukt ? 1 : 0);
