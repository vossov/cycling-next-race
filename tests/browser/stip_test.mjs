import { readFileSync } from 'fs';
const tekst = readFileSync('custom_components/cycling_next_race/www/cycling-next-race-card.js', 'utf8');

function body(naam) {
  const start = tekst.indexOf(`function ${naam}(entity)`);
  let d = 0, i = tekst.indexOf('{', start);
  for (let j = i; j < tekst.length; j++) {
    if (tekst[j] === '{') d++;
    else if (tekst[j] === '}') { d--; if (d === 0) return tekst.slice(start, j + 1); }
  }
}

const bron = body('svgTegel') + '\n' + body('svgDetail');
const maak = new Function(bron + '; return {svgTegel, svgDetail};');
const { svgTegel, svgDetail } = maak();

const ele = [];
for (let k = 0; k <= 180; k += 2) ele.push([k, 100 + 400 * Math.sin(k / 30)]);
const basis = {
  eyebrow: 'Etappe 18 · Vuelta', departure: 'A', arrival: 'B',
  distance_km: 180, vertical_m: 2900, elevation: ele, climbs: [],
  sprints: [60], show_state: 'LIVE', start_time: '13:10', finish_est: '17:25',
  watchability: 8, profile_score: 200,
};

function keur(naam, svg) {
  if (!svg.startsWith('<svg') || !svg.endsWith('</svg>')) throw new Error(naam + ': geen svg');
  for (const woord of ['NaN', 'undefined', 'null', 'Infinity']) {
    if (svg.includes(woord)) throw new Error(naam + ': bevat ' + woord);
  }
  return svg;
}

// 1. schatting
let a = Object.assign({}, basis, { est_km_to_go: 62.5, est_pct: 65 });
let t = keur('tegel/schatting', svgTegel({ attributes: a }));
let d = keur('detail/schatting', svgDetail({ attributes: a }));
console.log('tegel open ring :', /stroke-dasharray="3\.2 2\.6"/.test(t));
console.log('tegel geen puls :', !/animate/.test(t));
console.log('detail label    :', /SCHATTING/.test(d));
console.log('detail geen puls:', !/animate/.test(d));

// 2. echte meting gaat vóór de schatting
a = Object.assign({}, basis, { est_km_to_go: 62.5, live_km_to_go: 20 });
t = keur('tegel/meting', svgTegel({ attributes: a }));
d = keur('detail/meting', svgDetail({ attributes: a }));
console.log('meting pulseert :', /animate/.test(t) && /animate/.test(d));
console.log('meting geen lbl :', !/SCHATTING/.test(d));

// 3. niets live
a = Object.assign({}, basis, { show_state: 'Morgen' });
t = keur('tegel/leeg', svgTegel({ attributes: a }));
d = keur('detail/leeg', svgDetail({ attributes: a }));
console.log('zonder stip     :', !/SCHATTING/.test(d));

// 4. randgevallen: stip buiten het profiel, en rommel
for (const v of [0, -5, 999, 'x', null, undefined]) {
  keur('rand ' + v, svgDetail({ attributes: Object.assign({}, basis, { est_km_to_go: v }) }));
}
console.log('randgevallen    : ok');
