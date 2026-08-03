/*
 * Controleert of de kaart parseert als ES2018.
 *
 * Home Assistant laadt de kaart met add_extra_js_url, dus het script staat
 * op élke frontend-pagina. Eén stukje te nieuwe syntax is een SyntaxError
 * bij het parsen: de module draait dan helemaal niet en het custom element
 * registreert nooit — op elk apparaat met een oudere WebView.
 *
 * ES2018 hoort bij Chrome 60/61, de WebView van Android 8. Dat is wat er op
 * wandpanelen nog draait. Optional chaining (?.) en ?? zijn ES2020 en
 * sneuvelen hier dus.
 *
 * Let op: esbuild --target=chrome61 is hiervoor géén controle. Dat
 * transpileert de syntax weg en meldt niets; deze parser weigert juist.
 *
 *   npm install acorn
 *   node tests/browser/syntax_test.mjs
 */
import * as acorn from 'acorn';
import fs from 'fs';

const BESTAND = new URL(
  '../../custom_components/cycling_next_race/www/cycling-next-race-card.js',
  import.meta.url,
).pathname;

const DOEL = 2018; // Chrome 60/61

const bron = fs.readFileSync(BESTAND, 'utf8');
let mislukt = 0;

try {
  acorn.parse(bron, { ecmaVersion: DOEL, sourceType: 'module' });
  console.log(`ok    parseert als ES${DOEL} (Chrome 60/61)`);
} catch (e) {
  const regel = bron.slice(0, e.pos).split('\n').length;
  console.log(`FOUT  parseert niet als ES${DOEL}: ${e.message}`);
  console.log(`      regel ${regel}: ${bron.split('\n')[regel - 1].trim().slice(0, 100)}`);
  mislukt++;
}

// controleer dat de parser scherp genoeg staat: te nieuwe syntax moet vallen
for (const [naam, code] of [
  ['optional chaining', 'const a = b?.c;'],
  ['nullish coalescing', 'const a = b ?? c;'],
  ['logische toewijzing', 'let a; a ||= 1;'],
]) {
  try {
    acorn.parse(code, { ecmaVersion: DOEL, sourceType: 'module' });
    console.log(`FOUT  ${naam} wordt niet afgevangen — de controle staat te soepel`);
    mislukt++;
  } catch {
    /* zoals bedoeld */
  }
}
if (!mislukt) console.log('ok    de controle vangt ?., ?? en ||= af');

process.exit(mislukt ? 1 : 0);
