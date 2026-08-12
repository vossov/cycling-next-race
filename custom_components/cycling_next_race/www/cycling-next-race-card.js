/*
 * Cycling Next Race - Lovelace-kaart
 *
 * Wordt door de integratie zelf geregistreerd; je hoeft niets aan
 * resources of button_card_templates toe te voegen. Op je dashboard:
 *
 *   type: custom:cycling-next-race-card
 *
 * Opties (allemaal ook in de visuele editor, YAML is nergens nodig):
 *   entity        standaard sensor.cycling_next_race
 *   view          'profile' (standaard) toont het hoogteprofiel,
 *                 'countdown' een regel met de koers en het aftellen
 *   design        vormgeving: 'default' (eigen opmaak), 'ha' (volgt het
 *                 Home Assistant-thema) of 'bubble' (in de trant van
 *                 Bubble Card, maar zonder die kaart nodig te hebben)
 *   visible_days  vanaf hoeveel dagen voor de koers de kaart verschijnt:
 *                 2 is vandaag en morgen, 7 de hele week, 0 altijd.
 *                 Standaard 2 bij profile en 0 bij countdown
 *   details       true (standaard) opent bij een tik het volledige overzicht
 *   sections      welke onderdelen in dat overzicht staan; niets gekozen
 *                 betekent alles (zie SECTIES)
 *   title         eigen kop boven de kaart; leeg is geen kop
 *
 * Lopen er meerdere koersen tegelijk, dan staan ze in dat overzicht als
 * knoppen naast elkaar; de koers van de tegel staat open.
 *
 * always_show uit oudere configuraties blijft werken en betekent
 * visible_days: 0.
 *
 * De hoogteprofielen komen uit dezelfde tekencode die eerder als
 * button-card-template werd meegeleverd.
 */

const CAT = { HC: '#E4572E', 1: '#F2A03D', 2: '#EBD24A', 3: '#7FB069', 4: '#5FA8A0' };

/* De onderdelen van het detailvenster, in de volgorde waarin ze staan.
 * Wie er een aan- of uitzet doet dat met `sections`; niets gekozen betekent
 * alles, zodat een kaart zonder die optie blijft tonen wat hij altijd toonde. */
const SECTIES = [
  { key: 'profile', label: 'Hoogteprofiel' },
  { key: 'tv', label: 'Tv-zenders' },
  { key: 'upcoming', label: 'Komende dagen' },
  { key: 'result', label: 'Uitslag' },
  { key: 'gc', label: 'Algemeen klassement' },
  { key: 'points', label: 'Puntenklassement' },
  { key: 'kom', label: 'Bergklassement' },
  { key: 'youth', label: 'Jongerenklassement' },
];

const SECTIE_SLEUTELS = SECTIES.map(function (s) { return s.key; });

/* De vormgevingen. 'default' is de opmaak die de kaart altijd had; 'ha'
 * volgt de variabelen van het actieve Home Assistant-thema; 'bubble' is een
 * eigen nabootsing van de stijl van Bubble Card — die kaart zelf is er niet
 * voor nodig en wordt ook niet gebruikt. */
const VORMGEVING = [
  { value: 'default', label: 'Standaard (eigen opmaak)' },
  { value: 'ha', label: 'Home Assistant-thema' },
  { value: 'bubble', label: 'Bubble-stijl' },
];

const VORMGEVING_SLEUTELS = VORMGEVING.map(function (v) { return v.value; });

/** De vormgeving uit een configuratie; onbekend valt terug op 'default'. */
function vormgeving(waarde) {
  return VORMGEVING_SLEUTELS.indexOf(String(waarde)) >= 0 ? String(waarde) : 'default';
}

/** De gekozen secties; leeg of onzin betekent alles. */
function secties(waarde) {
  if (!Array.isArray(waarde)) return SECTIE_SLEUTELS.slice();
  const gekozen = waarde.filter(function (s) {
    return SECTIE_SLEUTELS.indexOf(String(s)) >= 0;
  }).map(String);
  return gekozen.length ? gekozen : SECTIE_SLEUTELS.slice();
}

/* ── hulpjes ─────────────────────────────────────────────────────── */

const esc = (s) =>
  String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

/** "52:14:33" of "1:20" naar seconden; null als het geen tijd is. */
function secs(t) {
  if (!t || String(t).indexOf(':') < 0) return null;
  const p = String(t).trim().split(':').map((x) => parseInt(x, 10));
  if (p.some((x) => !isFinite(x))) return null;
  return p.length === 3 ? p[0] * 3600 + p[1] * 60 + p[2] : p[0] * 60 + p[1];
}

/** Achterstand op de winnaar, zoals op een uitslagenpagina. */
function gap(t, winnaar) {
  const a = secs(t);
  const b = secs(winnaar);
  if (a == null || b == null) return t || '';
  const g = a - b;
  if (g <= 0) return 'z.t.';
  const m = Math.floor(g / 60);
  const s = g % 60;
  if (g < 3600) return `+${m}:${String(s).padStart(2, '0')}`;
  const u = Math.floor(g / 3600);
  return `+${u}:${String(Math.floor((g % 3600) / 60)).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

/** Stijging of daling in het klassement. */
function beweging(m) {
  if (!m) return '';
  const op = m > 0;
  return `<span class="mv" style="color:${op ? '#7FB069' : '#E4572E'}">${op ? '▲' : '▼'}${Math.abs(m)}</span>`;
}

/** Gewonnen of verloren tijd ten opzichte van de vorige etappe. */
function tijdwinst(s) {
  if (!s) return '';
  const verloren = s > 0;
  const a = Math.abs(s);
  const tekst = `${Math.floor(a / 60)}:${String(a % 60).padStart(2, '0')}`;
  return `<span class="mv" style="color:${verloren ? '#E4572E' : '#7FB069'}">${verloren ? '+' : '−'}${tekst}</span>`;
}

/* ── tekstblokken ────────────────────────────────────────────────── */

/** Renner met zijn ploeg erachter.
 *
 * Bij voorkeur de officiële ploegcode (`team_code`, drie letters), zoals
 * procyclingstats die op de ploegpagina noemt. Kent de sensor hem nog
 * niet — hij haalt er een paar per ronde op — dan staat de volledige naam
 * er zolang. Naam en ploeg delen hetzelfde vakje, zodat op een smal
 * scherm eerst de ploeg wegvalt en de rennernaam blijft staan.
 */
function rennerMetPloeg(x) {
  const ploeg = x.team_code || x.team;
  const achter = ploeg ? `<span class="ploeg">(${esc(ploeg)})</span>` : '';
  return `<span class="naam">${esc(x.rider)}${achter}</span>`;
}

/** Uitslag of klassement op tijd (uitslag, algemeen, jongeren). */
function tijdlijst(titel, rijen, opties = {}) {
  if (!rijen || !rijen.length) return '';
  const regels = rijen
    .map((x, i) => {
      const tijd = i === 0 ? x.time || '' : gap(x.time, rijen[0].time);
      const extra = opties.verschillen
        ? beweging(x.move) + tijdwinst(x.gain_s)
        : '';
      return `<li><span class="pos">${esc(x.rank)}</span>${rennerMetPloeg(x)}<span class="wrd">${esc(tijd)}${extra}</span></li>`;
    })
    .join('');
  return `<section><h3>${esc(titel)}</h3><ol>${regels}</ol></section>`;
}

/** Klassement op punten (punten, berg). */
function puntenlijst(titel, rijen) {
  if (!rijen || !rijen.length) return '';
  const regels = rijen
    .map((x) => {
      const winst = x.gain ? `<span class="mv" style="color:#7FB069">+${esc(x.gain)}</span>` : '';
      return `<li><span class="pos">${esc(x.rank)}</span>${rennerMetPloeg(x)}<span class="wrd">${esc(x.points)}${beweging(x.move)}${winst}</span></li>`;
    })
    .join('');
  return `<section><h3>${esc(titel)}</h3><ol>${regels}</ol></section>`;
}

/** Compacte regel met de koers en hoe lang het nog duurt.
 *
 * Bedoeld om altijd op het dashboard te staan, ook buiten een ronde: een
 * tik erop opent hetzelfde venster met de laatste uitslag.
 */
function aftelling(a) {
  const naam = a.race_name || a.eyebrow || 'Wielrennen';
  const wanneer = a.countdown || a.show_state || '';
  const live = /LIVE/i.test(a.show_state || '') || a.is_live === true;
  const onder = [a.date, a.type].filter(Boolean).join(' · ');

  return `
    <div class="aftel">
      <div class="aftel-icoon ${live ? 'live' : ''}">
        <svg viewBox="0 0 24 24" width="26" height="26" fill="currentColor" aria-hidden="true">
          <path d="M5 20.5A3.5 3.5 0 0 1 1.5 17A3.5 3.5 0 0 1 5 13.5A3.5 3.5 0 0 1 8.5 17A3.5 3.5 0 0 1 5 20.5M5 12a5 5 0 0 0-5 5a5 5 0 0 0 5 5a5 5 0 0 0 5-5a5 5 0 0 0-5-5m14.8-2H19V7h-1.5l-1.6-3.2A1 1 0 0 0 15 3.3l-1.9 1.1a1 1 0 0 0-.4 1.4l2 3.4l-2.2 2.6l-2.3-1.6l1.1-1.9l-1.7-1l-2.1 3.6l4.6 3.2l3.1-3.7l1.4 2.4A5 5 0 0 0 14 17a5 5 0 0 0 5 5a5 5 0 0 0 5-5a5 5 0 0 0-4.2-4.9M19 20.5A3.5 3.5 0 0 1 15.5 17a3.5 3.5 0 0 1 3.5-3.5a3.5 3.5 0 0 1 3.5 3.5a3.5 3.5 0 0 1-3.5 3.5"/>
        </svg>
      </div>
      <div class="aftel-tekst">
        <div class="aftel-naam">${esc(naam)}</div>
        ${onder ? `<div class="aftel-onder">${esc(onder)}</div>` : ''}
      </div>
      <div class="aftel-wanneer ${live ? 'live' : ''}">${esc(wanneer)}</div>
    </div>
  `;
}

/* ── koersen naast elkaar ────────────────────────────────────────── */

/* De sensor kan meerdere koersen tegelijk aanbieden (mannen en vrouwen
 * koersen vaak op dezelfde dag). Die staan in het attribuut `races`: de
 * eerste is de koers die ook op de tegel staat en heeft `primary: true`,
 * want al zijn gegevens staan al in de gewone attributen. De andere
 * dragen hun eigen uitslag en standen mee; hun hoogteprofiel staat in
 * `upcoming`, waar elke etappe met `race_key` bij een koers hoort. */

/** De koersen uit de attributen; altijd minstens één. */
function koersen(a) {
  const lijst = a.races;
  if (lijst && lijst.length) return lijst;
  return [{ primary: true, race_name: a.race_name || '', label: a.race_name || 'Wielrennen' }];
}

/* De sensor geeft per koers de kleur van de leiderstrui mee (`jersey`),
 * maar alleen waar die vaststaat. Ontbreekt hij, dan houdt de knop de
 * gewone accentkleur — een verzonnen kleur is erger dan geen kleur. */

const ACCENT = '#E4572E';

/** Alleen een echte hexkleur; de rest gaat als '' de opmaak niet in. */
function veiligeKleur(k) {
  return /^#[0-9a-fA-F]{3,8}$/.test(String(k == null ? '' : k)) ? String(k) : '';
}

/** Zwarte of witte letters op een gekleurde knop; geel wil zwart. */
function tekstOp(kleur) {
  const m = /^#([0-9a-fA-F]{6})$/.exec(kleur);
  if (!m) return '#fff';
  const n = parseInt(m[1], 16);
  const helder =
    (0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
  return helder > 0.6 ? '#0E1520' : '#fff';
}

/** De stijl van de open knop: de leiderstrui, anders het accent.
 *
 * In de Home Assistant-vormgeving is dat accent de primaire kleur van het
 * actieve thema. Of daar zwarte of witte letters op moeten is hier niet te
 * berekenen — het is een CSS-variabele en geen hexwaarde — dus komt de
 * letterkleur uit `--text-primary-color`, waar Home Assistant precies dat
 * in bijhoudt. Een echte truikleur blijft in elke vormgeving de truikleur.
 */
function knopStijl(race, design) {
  const trui = veiligeKleur(race.jersey);
  if (trui) return `background:${trui};border-color:${trui};color:${tekstOp(trui)}`;
  if (design === 'ha') {
    const p = `var(--primary-color,${ACCENT})`;
    return `background:${p};border-color:${p};color:var(--text-primary-color,#fff)`;
  }
  return `background:${ACCENT};border-color:${ACCENT};color:${tekstOp(ACCENT)}`;
}

/** De komende etappes die bij deze koers horen. */
function komendVoor(a, race, meerdere) {
  const alles = a.upcoming || [];
  if (!meerdere || !race.key) return alles;
  // een sensor van vóór race_key: dan is er niets te filteren en blijft
  // de volledige lijst staan, zoals altijd
  if (!alles.some((u) => u.race_key)) return alles;
  return alles.filter((u) => u.race_key === race.key);
}

/** Alles van één koers: profiel, komende dagen, uitslag en klassementen.
 *
 * `gekozen` is de lijst uit `sections`; wat er niet in staat wordt
 * overgeslagen. De volgorde ligt hier vast en niet in de configuratie —
 * een lijst die ook de volgorde bepaalt levert bij een half ingevulde
 * keuze een onvoorspelbaar venster op.
 */
function koersblok(a, race, meerdere, gekozen) {
  const aan = (sleutel) => gekozen.indexOf(sleutel) >= 0;
  const eigen = komendVoor(a, race, meerdere);
  // de getoonde etappe van de tegelkoers staat niet in upcoming; die van een
  // andere koers is er juist de eerste van, en hoort dus niet nog eens
  // onder "Komende dagen"
  const profiel = race.primary ? a : eigen[0];
  // staat het profiel uit, dan wordt die eerste etappe nergens meer
  // getekend en hoort hij gewoon bij "Komende dagen" — anders viel hij
  // tussen wal en schip
  const komend = race.primary || !aan('profile') ? eigen : eigen.slice(1);
  const u = race.primary ? a : race;

  const delen = [
    aan('profile') && profiel ? svgDetail({ attributes: profiel }) : '',
    // elke koers zijn eigen zenders; een sensor van vóór `races` heeft ze
    // alleen bovenaan staan, en dan blijft het bij de tegelkoers
    aan('tv') ? zenders(race.primary ? a.channels_detail : u.channels_detail) : '',
    aan('upcoming') && komend.length
      ? `<section><h3>Komende dagen</h3>${svgKomend({ attributes: { upcoming: komend } })}</section>`
      : '',
    aan('result') ? tijdlijst(u.last_stage_label || 'Uitslag', u.last_result) : '',
    aan('gc') ? tijdlijst('Algemeen klassement', u.gc_top, { verschillen: true }) : '',
    aan('points') ? puntenlijst('Puntenklassement', u.points_top) : '',
    aan('kom') ? puntenlijst('Bergklassement', u.kom_top) : '',
    aan('youth')
      ? tijdlijst('Jongerenklassement', u.youth_top, { verschillen: true })
      : '',
  ];
  // alleen bij de tegelkoers: de losse uitslag van een oudere sensor, die
  // anders dubbel zou staan met het eigen blok van die koers
  if (race.primary && !meerdere && aan('result')) {
    delen.push(tijdlijst(a.other_label || '', a.other_result));
  }

  const inhoud = delen.join('');
  return inhoud.trim()
    ? inhoud
    : '<div class="leeg">Nog geen gegevens voor deze koers.</div>';
}

/** Tv-zenders met logo en uitzendtijd. */
function zenders(lijst) {
  if (!lijst || !lijst.length) return '';
  const items = lijst
    .map((c) => {
      // zonder logo blijft de naam staan; de spatie voorkomt "NPO 114:15"
      const merk = c.logo
        ? `<img src="${esc(c.logo)}" alt="${esc(c.name)}">`
        : `${esc(c.name)} `;
      return `<span class="zender">${merk}${esc(c.time || '')}</span>`;
    })
    .join('<span class="scheiding">·</span>');
  return `<div class="zenders">${items}</div>`;
}


/* ── hoogteprofielen ─────────────────────────────────────────────── */

/* Overgenomen uit de button-card-template cycling_profile. */
function svgTegel(entity) {
  const a=entity.attributes||{}, dist=Number(a.distance_km)||1;
  const RID='#AFC3D6',FIL='#5B7A99',ACC='#E4572E';
  const cl=(a.climbs||[]).filter(c=>Number(c.top_m)>0).map(c=>({k:String(c.category||'').toUpperCase(),f:Number(c.km_to_finish)||0})).sort((p,q)=>q.f-p.f);
  const ele=(a.elevation||[]).map(p=>[Number(p[0]),Number(p[1])]).filter(p=>isFinite(p[0])&&isFinite(p[1]));
  const hasEle=ele.length>1;
  const W=440,L=16,R=16,T=54,BAND=hasEle?58:0,fl=T+BAND,H=fl+(hasEle?14:4);
  const E=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  let s='<svg viewBox="0 0 '+W+' '+H+'" width="100%" xmlns="http://www.w3.org/2000/svg" style="display:block;font-family:-apple-system,Roboto,sans-serif;color:var(--primary-text-color,#E8EEF4)">';
  s+='<defs><linearGradient id="wt" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="'+FIL+'" stop-opacity=".5"/><stop offset="1" stop-color="'+FIL+'" stop-opacity=".03"/></linearGradient></defs>';
  s+='<text x="'+L+'" y="25" fill="currentColor" font-size="15" font-weight="700">'+E(a.eyebrow||'')+'</text>';
  let b=[Math.round(dist)+' km']; if(a.vertical_m)b.push(Math.round(a.vertical_m)+' hm'); const _w=Number(a.watchability)||0; if(_w)b.push('Watchscore '+_w+'/10');
  s+='<text x="'+L+'" y="42" fill="currentColor" opacity=".6" font-size="13.5">'+E(b.join('  ·  '))+'</text>';
  const st=(a.show_state||'')+''; if(st){const lv=st.toUpperCase()=='LIVE',bt=lv?('LIVE'+(a.finish_est?'  ·  '+a.finish_est:'')):((st==='Vandaag'||st==='Morgen')&&a.start_time?(st+' '+String(a.start_time).trim()+(a.finish_est?'-'+a.finish_est:'')):st.toUpperCase()),tw=bt.length*8.2+22,px=W-R-tw; s+='<rect x="'+px.toFixed(1)+'" y="16" width="'+tw.toFixed(1)+'" height="24" rx="12" fill="'+(lv?ACC:'none')+'" stroke="'+(lv?ACC:'currentColor')+'" stroke-opacity="'+(lv?0:.5)+'"/><text x="'+(px+tw/2).toFixed(1)+'" y="32.5" text-anchor="middle" font-size="12.5" font-weight="700" fill="'+(lv?'#fff':'currentColor')+'" opacity="'+(lv?1:.7)+'">'+E(bt)+'</text>';}
  if(hasEle){
  const xmax=ele[ele.length-1][0]||dist, ys=ele.map(p=>p[1]), emin=Math.min(...ys), emax=Math.max(...ys), rng=Math.max(emax-emin,1);
  const y0=emin-rng*.12, y1=emax+rng*.10;
  const X=k=>L+(k/xmax)*(W-L-R), Y=v=>fl-((v-y0)/Math.max(y1-y0,1))*(fl-T);
  let d='M '+ele.map(p=>X(p[0]).toFixed(1)+','+Y(p[1]).toFixed(1)).join(' L ');
  s+='<path d="'+d+' L '+X(xmax).toFixed(1)+','+fl+' L '+X(ele[0][0]).toFixed(1)+','+fl+' Z" fill="url(#wt)"/><path d="'+d+'" fill="none" stroke="'+RID+'" stroke-width="1.8" stroke-linejoin="round"/>';
  const eleAt=k=>{if(k<=ele[0][0])return ele[0][1];if(k>=xmax)return ele[ele.length-1][1];for(let i=1;i<ele.length;i++){if(ele[i][0]>=k){const t=(k-ele[i-1][0])/((ele[i][0]-ele[i-1][0])||1);return ele[i-1][1]+t*(ele[i][1]-ele[i-1][1]);}}return ele[ele.length-1][1];};
  (a.sprints||[]).forEach(v=>{const f=Number(v);if(!isFinite(f)||f<=0||f>=xmax)return;const km=xmax-f,sx=X(km).toFixed(1),sy=Y(eleAt(km));s+='<circle cx="'+sx+'" cy="'+sy.toFixed(1)+'" r="3.2" fill="currentColor" opacity=".85"/><text x="'+sx+'" y="'+(sy-8).toFixed(1)+'" text-anchor="middle" font-size="11.5" font-weight="700" fill="currentColor" opacity=".85">S</text>';});
  cl.forEach(c=>{if(!c.k)return;const km=xmax-c.f,cx=X(km),cy=Y(eleAt(km));s+='<circle cx="'+cx.toFixed(1)+'" cy="'+cy.toFixed(1)+'" r="3.2" fill="currentColor" opacity=".85"/>';s+='<text x="'+cx.toFixed(1)+'" y="'+(cy-8).toFixed(1)+'" text-anchor="middle" font-size="11.5" font-weight="700" fill="currentColor" opacity=".85">'+E(c.k)+'</text>';});
  const lkm=Number(a.live_km_to_go);if(isFinite(lkm)&&lkm>0&&lkm<xmax){const lx=X(xmax-lkm).toFixed(1),ly=Y(eleAt(xmax-lkm)).toFixed(1);s+='<circle cx="'+lx+'" cy="'+ly+'" r="5" fill="#E4572E" stroke="#fff" stroke-width="1.8"><animate attributeName="r" values="5;7;5" dur="1.4s" repeatCount="indefinite"/></circle>';}
  } else {
  const sc=Number(a.profile_score)||0, vm=Number(a.vertical_m)||0;
  const terr=(sc>=150||vm>=3000)?'Bergrit':(sc>=50||vm>=1500)?'Heuvelachtig':(sc||vm||cl.length)?'Vlakke etappe':'Profiel nog niet bekend';
  s+='<text x="'+L+'" y="'+(T+2)+'" font-size="13" fill="currentColor" opacity=".55">'+E(terr+(cl.length?'  ·  '+cl.length+' cols':''))+'</text>';
  }
  s+='</svg>'; return s;
}

/* Overgenomen uit de button-card-template cycling_detail. */
function svgDetail(entity) {
  const a=entity.attributes||{}, dist=Number(a.distance_km)||1;
  const CAT={HC:'#E4572E','1':'#F2A03D','2':'#EBD24A','3':'#7FB069','4':'#5FA8A0'};
  const RID='#AFC3D6',FIL='#5B7A99',ACC='#E4572E';
  const cl=(a.climbs||[]).filter(c=>Number(c.top_m)>0).map(c=>({n:c.name||'',k:String(c.category||'').toUpperCase(),x:dist-(Number(c.km_to_finish)||0),t:Number(c.top_m),f:Number(c.km_to_finish)||0,l:Number(c.length_km)||0,s:Number(c.steepness_pct)||0})).sort((p,q)=>p.x-q.x);
  const ele=(a.elevation||[]).map(p=>[Number(p[0]),Number(p[1])]).filter(p=>isFinite(p[0])&&isFinite(p[1]));
  const hasEle=ele.length>1;
  const W=440,L=16,R=16,T=74,rows=Math.min(6,cl.length),PH=hasEle?85:0,legH=cl.length?12+rows*30:0,B=cl.length?legH+14:18,H=T+PH+B,fl=T+PH;
  const E=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'), N=x=>x==null?'':String(Math.round(x*10)/10).replace('.',',');
  let s='<svg viewBox="0 0 '+W+' '+H+'" width="100%" xmlns="http://www.w3.org/2000/svg" style="display:block;font-family:-apple-system,Roboto,sans-serif;color:var(--primary-text-color,#E8EEF4)">';
  s+='<defs><linearGradient id="wt" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="'+FIL+'" stop-opacity=".55"/><stop offset="1" stop-color="'+FIL+'" stop-opacity=".03"/></linearGradient></defs>';
  s+='<text x="'+L+'" y="20" fill="currentColor" opacity=".6" font-size="11" font-weight="700" letter-spacing="1.3">'+E((a.eyebrow||'').toUpperCase())+'</text>';
  s+='<text x="'+L+'" y="45" fill="currentColor" font-size="20" font-weight="700">'+E((a.departure&&a.arrival)?a.departure+' → '+a.arrival:(a.eyebrow||''))+'</text>';
  let b=[Math.round(dist)+' km']; if(a.vertical_m)b.push(Math.round(a.vertical_m)+' hm'); const _w=Number(a.watchability)||0; if(_w)b.push('Watchscore '+_w+'/10');
  s+='<text x="'+L+'" y="65" fill="currentColor" opacity=".6" font-size="13.5">'+E(b.join('  ·  '))+'</text>';
  const st=(a.show_state||'')+''; if(st){const lv=st.toUpperCase()=='LIVE',bt=lv?('LIVE'+(a.finish_est?'  ·  '+a.finish_est:'')):((st==='Vandaag'||st==='Morgen')&&a.start_time?(st+' '+String(a.start_time).trim()+(a.finish_est?'-'+a.finish_est:'')):st.toUpperCase()),tw=bt.length*8.2+22,px=W-R-tw; s+='<rect x="'+px.toFixed(1)+'" y="16" width="'+tw.toFixed(1)+'" height="24" rx="12" fill="'+(lv?ACC:'none')+'" stroke="'+(lv?ACC:'currentColor')+'" stroke-opacity="'+(lv?0:.5)+'"/><text x="'+(px+tw/2).toFixed(1)+'" y="32.5" text-anchor="middle" font-size="12.5" font-weight="700" fill="'+(lv?'#fff':'currentColor')+'" opacity="'+(lv?1:.7)+'">'+E(bt)+'</text>';}
  if(hasEle){
  const xmax=ele[ele.length-1][0]||dist;
  const ys=ele.map(p=>p[1]), emin=Math.min(...ys), emax=Math.max(...ys), rng=Math.max(emax-emin,1);
  const y0=emin-rng*0.12, y1=emax+rng*0.08;
  const X=k=>L+(k/xmax)*(W-L-R), Y=v=>fl-((v-y0)/Math.max(y1-y0,1))*(fl-T);
  let d='M '+ele.map(p=>X(p[0]).toFixed(1)+','+Y(p[1]).toFixed(1)).join(' L ');
  s+='<path d="'+d+' L '+X(xmax).toFixed(1)+','+fl+' L '+X(ele[0][0]).toFixed(1)+','+fl+' Z" fill="url(#wt)"/><path d="'+d+'" fill="none" stroke="'+RID+'" stroke-width="2" stroke-linejoin="round"/>';
  const eleAt=k=>{if(k<=ele[0][0])return ele[0][1];if(k>=xmax)return ele[ele.length-1][1];for(let i=1;i<ele.length;i++){if(ele[i][0]>=k){const t=(k-ele[i-1][0])/((ele[i][0]-ele[i-1][0])||1);return ele[i-1][1]+t*(ele[i][1]-ele[i-1][1]);}}return ele[ele.length-1][1];};
  (a.sprints||[]).forEach(v=>{const f=Number(v);if(!isFinite(f)||f<=0||f>=xmax)return;const km=xmax-f,sx=X(km).toFixed(1),sy=Y(eleAt(km));s+='<circle cx="'+sx+'" cy="'+sy.toFixed(1)+'" r="4" fill="currentColor" opacity=".85"/><text x="'+sx+'" y="'+(sy-9).toFixed(1)+'" text-anchor="middle" font-size="12" font-weight="700" fill="currentColor" opacity=".85">S</text>';});
  cl.forEach((c,i)=>{const km=xmax-(Number(c.f)||0),cx=X(km).toFixed(1),cy=Y(eleAt(km)).toFixed(1);s+='<circle cx="'+cx+'" cy="'+cy+'" r="11" fill="'+(CAT[c.k]||RID)+'" stroke="#0E1520" stroke-width="1.6"/><text x="'+cx+'" y="'+(Number(cy)+4.5).toFixed(1)+'" text-anchor="middle" font-size="13" font-weight="700" fill="#0E1520">'+(i+1)+'</text>';});
  const lkm=Number(a.live_km_to_go);if(isFinite(lkm)&&lkm>0&&lkm<xmax){const lx=X(xmax-lkm).toFixed(1),ly=Y(eleAt(xmax-lkm)).toFixed(1);s+='<line x1="'+lx+'" y1="'+ly+'" x2="'+lx+'" y2="'+fl+'" stroke="'+ACC+'" stroke-width="1.5" stroke-dasharray="2 3" opacity=".65"/><circle cx="'+lx+'" cy="'+ly+'" r="6" fill="'+ACC+'" stroke="#fff" stroke-width="2"><animate attributeName="r" values="6;8.5;6" dur="1.4s" repeatCount="indefinite"/></circle>';}
  } else {
  const sc=Number(a.profile_score)||0, vm=Number(a.vertical_m)||0;
  const terr=(sc>=150||vm>=3000)?'Bergrit':(sc>=50||vm>=1500)?'Heuvelachtig':(sc||vm||cl.length)?'Vlakke etappe':'Profiel nog niet bekend';
  s+='<text x="'+L+'" y="'+(T+12)+'" font-size="14" fill="currentColor" opacity=".6">'+E(terr+(cl.length?'  ·  geen hoogtelijn beschikbaar':''))+'</text>';
  }
  if(cl.length){const ly=fl+26; cl.slice(0,6).forEach((c,i)=>{const col=CAT[c.k]||RID,y=ly+i*30,nm=(c.n||'').length>22?c.n.slice(0,21)+'…':c.n; let m=[]; if(c.f!=null)m.push('op '+Math.round(c.f)+' km'); if(c.l)m.push(N(c.l)+' km @ '+N(c.s)+'%'); s+='<circle cx="'+(L+10)+'" cy="'+(y-5)+'" r="9" fill="'+col+'"/><text x="'+(L+10)+'" y="'+(y-1)+'" text-anchor="middle" font-size="11" font-weight="700" fill="#0E1520">'+(i+1)+'</text><text x="'+(L+27)+'" y="'+y+'" font-size="15" font-weight="600" fill="currentColor">'+E(nm)+'</text><text x="'+(W-R)+'" y="'+y+'" text-anchor="end" font-size="12" fill="currentColor" opacity=".6">'+E(m.join(' · '))+'</text>';});}
  s+='</svg>'; return s;
}

/* Overgenomen uit de button-card-template cycling_upcoming. */
function svgKomend(entity) {
  const up=entity.attributes.upcoming||[];
  const RID='#AFC3D6',FIL='#5B7A99';
  const CAT={HC:'#E4572E','1':'#F2A03D','2':'#EBD24A','3':'#7FB069','4':'#5FA8A0'};
  const W=440,L=16,R=16,BAND=52,RANGE_MAX=2200,MPU=BAND/RANGE_MAX;
  const E=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'), N=x=>x==null?'':String(Math.round(x*10)/10).replace('.',',');
  if(!up.length) return '<svg viewBox="0 0 '+W+' 40" width="100%" xmlns="http://www.w3.org/2000/svg" style="font-family:-apple-system,Roboto,sans-serif;color:var(--primary-text-color,#E8EEF4)"><text x="'+L+'" y="24" font-size="13" fill="currentColor" opacity=".6">Geen komende etappes</text></svg>';
  const items=up.map(u=>{const cl=(u.climbs||[]).filter(c=>Number(c.top_m)>0).sort((a,b)=>(Number(b.km_to_finish)||0)-(Number(a.km_to_finish)||0));const nc=Math.min(4,cl.length);const he=(u.elevation||[]).length>1;const bh=he?BAND:18;return {u,cl,nc,he,bh,h:42+bh+(nc?6+nc*15:0)+14};});
  const H=items.reduce((a,it)=>a+it.h,0)+6;
  let s='<svg viewBox="0 0 '+W+' '+H+'" width="100%" xmlns="http://www.w3.org/2000/svg" style="display:block;font-family:-apple-system,Roboto,sans-serif;color:var(--primary-text-color,#E8EEF4)">';
  s+='<defs><linearGradient id="uw" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="'+FIL+'" stop-opacity=".5"/><stop offset="1" stop-color="'+FIL+'" stop-opacity=".03"/></linearGradient></defs>';
  let oy=4;
  for(const it of items){
  const u=it.u, dist=Number(u.distance_km)||1, cl=it.cl;
  const sc=Number(u.profile_score)||0, vm=Number(u.vertical_m)||0;
  const onbekend=!it.he&&!cl.length&&!sc&&!vm;
  s+='<text x="'+L+'" y="'+(oy+16)+'" font-size="14" font-weight="700" fill="currentColor">'+E(u.eyebrow||'')+'</text>';
  const ss=(u.show_state||'')+''; s+='<text x="'+(W-R)+'" y="'+(oy+16)+'" text-anchor="end" font-size="11.5" font-weight="700" fill="currentColor" opacity=".55">'+E(ss.toUpperCase())+'</text>';
  let meta=[]; if(u.departure&&u.arrival)meta.push(u.departure+' → '+u.arrival); meta.push(Math.round(dist)+' km'); if(u.vertical_m)meta.push(Math.round(u.vertical_m)+' hm'); const _w=Number(u.watchability)||0; if(_w&&!onbekend)meta.push('Watchscore '+_w+'/10');
  s+='<text x="'+L+'" y="'+(oy+33)+'" font-size="12" fill="currentColor" opacity=".6">'+E(meta.join(' · '))+'</text>';
  const bT=oy+42, bB=oy+42+it.bh;
  const ele=(u.elevation||[]).map(p=>[Number(p[0]),Number(p[1])]).filter(p=>isFinite(p[0])&&isFinite(p[1]));
  if(ele.length>1){
  const xmax=ele[ele.length-1][0]||dist, ys=ele.map(p=>p[1]), emin=Math.min(...ys);
  const X=k=>L+(k/xmax)*(W-L-R), Y=v=>Math.max(bB-(v-emin)*MPU,bT);
  let d='M '+ele.map(p=>X(p[0]).toFixed(1)+','+Y(p[1]).toFixed(1)).join(' L ');
  s+='<path d="'+d+' L '+X(xmax).toFixed(1)+','+bB+' L '+X(ele[0][0]).toFixed(1)+','+bB+' Z" fill="url(#uw)"/><path d="'+d+'" fill="none" stroke="'+RID+'" stroke-width="1.6" stroke-linejoin="round"/>';
  const eleAt=k=>{if(k<=ele[0][0])return ele[0][1];if(k>=xmax)return ele[ele.length-1][1];for(let i=1;i<ele.length;i++){if(ele[i][0]>=k){const t=(k-ele[i-1][0])/((ele[i][0]-ele[i-1][0])||1);return ele[i-1][1]+t*(ele[i][1]-ele[i-1][1]);}}return ele[ele.length-1][1];};
  (u.sprints||[]).forEach(v=>{const f=Number(v);if(!isFinite(f)||f<=0||f>=xmax)return;const km=xmax-f,sx=X(km).toFixed(1),sy=Y(eleAt(km));s+='<circle cx="'+sx+'" cy="'+sy.toFixed(1)+'" r="2.6" fill="currentColor" opacity=".8"/><text x="'+sx+'" y="'+(sy-6).toFixed(1)+'" text-anchor="middle" font-size="9" font-weight="700" fill="currentColor" opacity=".8">S</text>';});
  cl.forEach((c,i)=>{const km=xmax-(Number(c.km_to_finish)||0),cx=X(km).toFixed(1),cy=Y(eleAt(km)).toFixed(1),col=CAT[String(c.category||'').toUpperCase()]||RID;s+='<circle cx="'+cx+'" cy="'+cy+'" r="6.5" fill="'+col+'" stroke="#0E1520" stroke-width="1.2"/><text x="'+cx+'" y="'+(Number(cy)+2.7).toFixed(1)+'" text-anchor="middle" font-size="8.5" font-weight="700" fill="#0E1520">'+(i+1)+'</text>';});
  } else {
  const terr=onbekend?'Profiel nog niet bekend':((sc>=150||vm>=3000)?'Bergrit':(sc>=50||vm>=1500)?'Heuvelachtig':'Vlak');
  s+='<text x="'+L+'" y="'+(bT+12)+'" font-size="11" fill="currentColor" opacity=".45">'+E(terr+(cl.length?'  ·  '+cl.length+' cols':''))+'</text>';
  }
  const HV=cl.map((c,i)=>i).sort((x,y)=>((Number(cl[y].length_km)||0)*(Number(cl[y].steepness_pct)||0))-((Number(cl[x].length_km)||0)*(Number(cl[x].steepness_pct)||0))).slice(0,4).sort((x,y)=>x-y);
  HV.forEach((ci,row)=>{const c=cl[ci], ty=bB+18+row*15, col=CAT[String(c.category||'').toUpperCase()]||RID, nm=(c.name||'').length>28?c.name.slice(0,27)+'…':c.name, l=Number(c.length_km)||0, st=Number(c.steepness_pct)||0;
  s+='<circle cx="'+(L+6)+'" cy="'+(ty-4)+'" r="6" fill="'+col+'"/><text x="'+(L+6)+'" y="'+(ty-1.2)+'" text-anchor="middle" font-size="8" font-weight="700" fill="#0E1520">'+(ci+1)+'</text>';
  if(nm)s+='<text x="'+(L+18)+'" y="'+ty+'" font-size="12" fill="currentColor" opacity=".85">'+E(nm)+'</text>';
  if(l)s+='<text x="'+(W-R)+'" y="'+ty+'" text-anchor="end" font-size="11" fill="currentColor" opacity=".5">'+E(N(l)+' km @ '+N(st)+'%')+'</text>';});
  s+='<line x1="'+L+'" y1="'+(oy+it.h-1)+'" x2="'+(W-R)+'" y2="'+(oy+it.h-1)+'" stroke="currentColor" stroke-opacity=".08"/>';
  oy+=it.h;
  }
  s+='</svg>'; return s;
}

/* ── de kaart ────────────────────────────────────────────────────── */

const STIJL = `
  :host { display: block; }
  ha-card { padding: 10px; overflow: hidden; }
  ha-card.klikbaar { cursor: pointer; }
  .leeg { padding: 16px; opacity: .6; font-size: 14px; }
  svg { display: block; width: 100%; height: auto; }

  .aftel { display: flex; align-items: center; padding: 2px 4px; }
  /* geen gap: die werkt pas vanaf Chrome 84 en oude wandpanelen
     draaien vaak ouder; marges doen hetzelfde en werken overal */
  .aftel > * + * { margin-left: 12px; }
  .aftel-icoon { flex: none; opacity: .75; line-height: 0; }
  .aftel-icoon svg { width: 26px; height: 26px; }
  .aftel-icoon.live { color: #E4572E; opacity: 1; }
  .aftel-tekst { flex: 1; min-width: 0; }
  .aftel-naam {
    font-size: 15px; font-weight: 700;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .aftel-onder { font-size: 12.5px; opacity: .6; margin-top: 1px; }
  .aftel-wanneer {
    flex: none; font-size: 13.5px; font-weight: 700; opacity: .8;
    white-space: nowrap;
  }
  .aftel-wanneer.live { color: #E4572E; opacity: 1; }

  dialog {
    border: none; border-radius: 22px; padding: 0; max-width: 560px; width: 92vw;
    max-height: 86vh; overflow: auto;
    background: var(--card-background-color, #1c1c1c);
    color: var(--primary-text-color, #e8eef4);
  }
  dialog::backdrop { background: rgba(0, 0, 0, .55); }
  .kop {
    display: flex; align-items: center;
    padding: 14px 18px 6px; font-size: 17px; font-weight: 700;
  }
  .kop .sluit {
    margin-left: auto; cursor: pointer; border: none; background: none;
    color: inherit; font-size: 22px; line-height: 1; padding: 4px 8px;
  }
  .inhoud { padding: 0 18px 18px; }

  /* de aanklikbare koersen; alleen zichtbaar als er meer dan één is */
  .koersen { display: flex; flex-wrap: wrap; padding: 4px 18px 0; }
  /* geen gap: die werkt pas vanaf Chrome 84 */
  .koersen > * + * { margin-left: 6px; }
  .koers {
    border: 1px solid var(--divider-color, #444); background: none;
    color: inherit; font: inherit; font-size: 13px; font-weight: 600;
    padding: 5px 12px; margin-bottom: 6px; border-radius: 14px;
    cursor: pointer; opacity: .65; white-space: nowrap;
  }
  .koers.aan { background: #E4572E; border-color: #E4572E; color: #fff; opacity: 1; }
  /* het stipje van de leiderstrui op een dichte knop; op de open knop staat
     die kleur al op de knop zelf, dus daar mag het stipje weg */
  .koers .trui {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    margin-right: 6px; vertical-align: middle;
  }
  .koers.aan .trui { display: none; }
  .blok.uit { display: none; }

  section { margin-top: 14px; }
  h3 { margin: 0 0 6px; font-size: 14px; font-weight: 700; }
  ol { list-style: none; margin: 0; padding: 0; font-size: 13.5px; }
  li { display: flex; padding: 2px 0; align-items: baseline; }
  li > * + * { margin-left: 8px; }
  .pos { width: 1.6em; text-align: right; opacity: .55; font-variant-numeric: tabular-nums; }
  .naam { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  /* de ploeg deelt het vakje met de rennernaam: wordt het krap, dan valt
     de ploeg als eerste weg en blijft de naam leesbaar */
  .ploeg { opacity: .5; font-size: 12px; margin-left: 5px; }
  .wrd { font-variant-numeric: tabular-nums; opacity: .85; white-space: nowrap; }
  .mv { margin-left: 6px; font-size: 12px; }

  .zenders { text-align: right; font-size: 13px; padding: 6px 0 2px; opacity: .9; }
  .zender { white-space: nowrap; }
  .zenders img { height: 20px; width: auto; border-radius: 3px;
                 vertical-align: middle; margin-right: 5px; }
  .scheiding { opacity: .45; margin: 0 6px; }

  /* een eigen kop boven de kaart; zonder de optie "title" staat hij er niet */
  .kaartkop {
    font-size: 15px; font-weight: 700; padding: 2px 4px 8px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }

  /* ── vormgeving: Home Assistant ──────────────────────────────────── */
  /* Volgt de variabelen van het actieve thema in plaats van onze eigen
     kleuren: dezelfde binnenmarge, dezelfde koptekst en dezelfde afronding
     als een ingebouwde kaart. Het accent wordt --primary-color; alleen de
     hoogteprofielen houden hun eigen kleuren, want die tekencode is gedeeld
     met de button-card-templates en mag niet uiteenlopen. */
  ha-card.thema-ha { padding: 8px 16px 16px; }
  .thema-ha .kaartkop {
    font-size: 24px; font-weight: 400; padding: 10px 0 16px;
    color: var(--ha-card-header-color, var(--primary-text-color, #e8eef4));
  }
  .thema-ha .aftel-icoon.live,
  .thema-ha .aftel-wanneer.live { color: var(--primary-color, #E4572E); }
  dialog.thema-ha {
    border-radius: var(--ha-card-border-radius, 12px);
    background: var(--ha-card-background, var(--card-background-color, #1c1c1c));
  }

  /* ── vormgeving: Bubble-stijl ────────────────────────────────────── */
  /* Nagebouwd, niet overgenomen: Bubble Card zelf is hier niet voor nodig
     en wordt ook niet gebruikt. Wat de stijl herkenbaar maakt is de sterke
     afronding, het icoon in een rondje, de status in een pilletje en een
     venster dat onder aan het scherm plakt. */
  ha-card.thema-bubble {
    border-radius: 32px; box-shadow: none; border: none; padding: 12px 14px;
    background: var(--ha-card-background, var(--card-background-color, #1c1c1c));
  }
  .thema-bubble .kaartkop { padding: 2px 8px 8px; }
  .thema-bubble .aftel-icoon {
    width: 38px; height: 38px; border-radius: 50%; opacity: 1;
    text-align: center;
    background: var(--secondary-background-color, rgba(127, 127, 127, .18));
  }
  .thema-bubble .aftel-icoon svg { width: 22px; height: 22px; margin-top: 8px; }
  .thema-bubble .aftel-wanneer {
    border-radius: 14px; padding: 4px 10px; opacity: 1;
    background: var(--secondary-background-color, rgba(127, 127, 127, .18));
  }
  .thema-bubble .koers { border-radius: 18px; padding: 6px 14px; }
  dialog.thema-bubble {
    border-radius: 32px 32px 0 0; width: 100%; max-width: 640px;
    /* onderaan plakken, zoals de pop-up van Bubble Card. Oudere WebViews
       plaatsen een modale dialog nog zelf; daar blijft hij in het midden
       staan — alleen de plaats klopt dan niet, de kaart werkt gewoon. */
    margin: auto auto 0;
  }
`;

class CyclingNextRaceCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement('cycling-next-race-card-editor');
  }

  /* De configuratie waarmee een nieuwe kaart begint.
   *
   * `sections` en `title` staan er bewust niet in. Een kaart zonder
   * `sections` toont alles, ook onderdelen die er later bij komen; zou de
   * volledige lijst hier staan, dan zou elke kaart die vandaag wordt
   * aangemaakt een toekomstig onderdeel stilzwijgend missen. En een lege
   * `title` is hetzelfde als geen title, dus die hoeft niet in de YAML.
   */
  static getStubConfig() {
    return {
      entity: 'sensor.cycling_next_race',
      view: 'profile',
      design: 'default',
      visible_days: 2,
      details: true,
    };
  }

  setConfig(config) {
    const gegeven = config || {};
    const view = gegeven.view === 'countdown' ? 'countdown' : 'profile';
    // de aftelweergave is bedoeld om er altijd te staan; het profiel
    // verschijnt standaard pas als de koers vandaag of morgen is
    this._config = {
      entity: 'sensor.cycling_next_race',
      view: view,
      design: 'default',
      visible_days: view === 'countdown' ? 0 : 2,
      details: true,
      sections: SECTIE_SLEUTELS.slice(),
      title: '',
      ...gegeven,
    };
    // always_show uit een oudere configuratie betekent: geen grens
    if (gegeven.always_show === true && gegeven.visible_days === undefined) {
      this._config.visible_days = 0;
    }
    delete this._config.always_show;
    // wat er ook in de configuratie stond, hierna staat er iets bruikbaars.
    // setConfig mag niets gooien: Home Assistant maakt van elke uitzondering
    // hier een foutkaart, en die is voor de gebruiker niet te repareren
    this._config.design = vormgeving(this._config.design);
    this._config.sections = secties(this._config.sections);
    this._config.entity = String(this._config.entity || 'sensor.cycling_next_race');
    this._vorigeStatus = null;
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    // meteen opnieuw tekenen. Bij een wijziging in het bewerkscherm komt er
    // geen nieuwe status voorbij, en zonder dit bleef de voorvertoning de
    // oude vormgeving tonen
    if (this._hass) this._teken(this._hass.states[this._config.entity]);
  }

  set hass(hass) {
    this._hass = hass;
    // hass vóór setConfig: er is nog niets om mee te tekenen. Een
    // uitzondering hier laat de kaart leeg achter
    if (!this._config) return;
    const st = hass && hass.states[this._config.entity];
    // alleen hertekenen als er echt iets veranderd is
    const stempel = st ? `${st.state}|${st.last_updated}` : 'weg';
    if (stempel === this._vorigeStatus) return;
    this._vorigeStatus = stempel;
    this._teken(st);
  }

  /* Home Assistant zet dit op kaarten in de kaartkiezer en het
   * bewerkscherm. Wordt het later gezet dan hass, dan moet de kaart alsnog
   * opnieuw getekend worden — anders blijft hij daar verborgen. */
  set preview(waarde) {
    const nieuw = Boolean(waarde);
    if (nieuw === this._preview) return;
    this._preview = nieuw;
    this._vorigeStatus = null;
    if (this._hass) this.hass = this._hass;
  }

  get preview() {
    return this._preview === true;
  }

  getCardSize() {
    return 3;
  }

  _teken(st) {
    const root = this.shadowRoot;
    if (!root) return;
    const thema = `thema-${this._config.design}`;
    if (!st) {
      root.innerHTML = `<style>${STIJL}</style><ha-card class="${thema}"><div class="leeg">${esc(this._config.entity)} bestaat niet.</div></ha-card>`;
      return;
    }

    const a = st.attributes || {};
    const dagen = Number(a.days_until);
    const grens = Number(this._config.visible_days);
    // grens 0 (of onzin) betekent: geen grens, altijd tonen
    const verbergen =
      isFinite(grens) && grens > 0 && isFinite(dagen) && dagen >= grens;

    // in de kaartkiezer en het bewerkscherm nooit verbergen: een kaart die
    // zichzelf onzichtbaar maakt is daar niet meer aan te klikken
    if ((verbergen || a.show_state === 'Klaar') && !this.preview) {
      root.innerHTML = '';
      this.style.display = 'none';
      return;
    }
    this.style.display = 'block';

    const klikbaar = this._config.details;
    const inhoud =
      this._config.view === 'countdown' ? aftelling(a) : svgTegel({ attributes: a });
    const kop = this._config.title
      ? `<div class="kaartkop">${esc(this._config.title)}</div>`
      : '';
    root.innerHTML = `
      <style>${STIJL}</style>
      <ha-card class="${thema}${klikbaar ? ' klikbaar' : ''}">${kop}${inhoud}</ha-card>
      ${klikbaar ? this._dialoog(a) : ''}
    `;

    if (klikbaar) {
      const dlg = root.querySelector('dialog');
      root.querySelector('ha-card').onclick = () => dlg.showModal();
      root.querySelector('.sluit').onclick = () => dlg.close();
      dlg.onclick = (e) => {
        if (e.target === dlg) dlg.close();
      };
      this._koersknoppen(dlg, a);
    }
  }

  _dialoog(a) {
    const races = koersen(a);
    const meerdere = races.length > 1;
    const design = this._config.design;

    // koersen mét naam eerst noemen in de kop; die volgt de keuze
    const keuze = meerdere
      ? `<div class="koersen">${races
          .map((r, i) => {
            const kleur = veiligeKleur(r.jersey);
            // dichte knop: de kleur staat op de knop zelf; de andere krijgen
            // een stipje, zodat de koers ook dicht herkenbaar blijft
            const stip = kleur
              ? `<span class="trui" style="background:${kleur}"></span>`
              : '';
            const stijl = i === 0 ? ` style="${knopStijl(r, design)}"` : '';
            return (
              `<button class="koers${i === 0 ? ' aan' : ''}" data-i="${i}"${stijl}>` +
              `${stip}${esc(r.label || r.race_name || 'Koers')}</button>`
            );
          })
          .join('')}</div>`
      : '';

    const gekozen = this._config.sections;
    const blokken = races
      .map(
        (r, i) =>
          `<div class="blok${i === 0 ? '' : ' uit'}">${koersblok(a, r, meerdere, gekozen)}</div>`
      )
      .join('');

    const kop = races[0].race_name || a.race_name || 'Wielrennen';
    return `
      <dialog class="thema-${design}">
        <div class="kop">
          <span class="titel">${esc(kop)}</span>
          <button class="sluit" aria-label="Sluiten">&times;</button>
        </div>
        ${keuze}
        <div class="inhoud">${blokken}</div>
      </dialog>
    `;
  }

  /** De koersknoppen bovenin de pop-up laten wisselen van blok. */
  _koersknoppen(dlg, a) {
    const knoppen = dlg.querySelectorAll('.koers');
    if (!knoppen.length) return;
    const blokken = dlg.querySelectorAll('.blok');
    const titel = dlg.querySelector('.titel');
    const races = koersen(a);
    const design = this._config.design;
    for (let i = 0; i < knoppen.length; i++) {
      knoppen[i].onclick = () => {
        for (let j = 0; j < knoppen.length; j++) {
          const aan = i === j;
          knoppen[j].className = aan ? 'koers aan' : 'koers';
          // de kleur van de leiderstrui verhuist mee naar de open knop
          knoppen[j].setAttribute('style', aan ? knopStijl(races[j] || {}, design) : '');
          blokken[j].className = aan ? 'blok' : 'blok uit';
        }
        const r = races[i] || {};
        if (titel) titel.textContent = r.race_name || r.label || '';
        // een langere lijst begint bij de gekozen koers weer bovenaan
        dlg.scrollTop = 0;
      };
    }
  }
}

// Het script kan langs twee wegen binnenkomen (Lovelace-resource of
// add_extra_js_url). Twee keer definiëren gooit een DOMException en breekt
// dan alsnog alles, dus eerst kijken of het er al is.
if (!customElements.get('cycling-next-race-card')) {
  customElements.define('cycling-next-race-card', CyclingNextRaceCard);
}

/* ── visuele editor ──────────────────────────────────────────────── */

/* Wat de gebruiker te zien krijgt achter de knop Bewerken. Home Assistant
 * levert ha-form mee; is dat er onverhoopt niet, dan volgt een eenvoudig
 * formulier met dezelfde velden. */

const VELDEN = [
  {
    name: 'entity',
    label: 'Sensor',
    uitleg: 'De sensor van Cycling Next Race.',
    selector: { entity: { domain: 'sensor', integration: 'cycling_next_race' } },
  },
  {
    name: 'view',
    label: 'Weergave',
    uitleg: 'Het hoogteprofiel, of een regel met de koers en het aftellen.',
    selector: {
      select: {
        mode: 'dropdown',
        options: [
          { value: 'profile', label: 'Hoogteprofiel' },
          { value: 'countdown', label: 'Aftellen' },
        ],
      },
    },
  },
  {
    name: 'design',
    label: 'Vormgeving',
    uitleg:
      'Eigen opmaak, het actieve Home Assistant-thema, of de stijl van ' +
      'Bubble Card — die laatste is nagebouwd, de kaart zelf heb je er niet ' +
      'voor nodig.',
    selector: { select: { mode: 'dropdown', options: VORMGEVING } },
  },
  {
    name: 'visible_days',
    label: 'Tonen vanaf (dagen voor de koers)',
    uitleg: '2 is vandaag en morgen, 7 is de hele week vooruit, 0 is altijd.',
    selector: { number: { min: 0, max: 60, mode: 'box', step: 1 } },
  },
  {
    name: 'details',
    label: 'Detailvenster bij aantikken',
    uitleg: 'Opent uitslag, klassementen en tv-zenders.',
    selector: { boolean: {} },
  },
  {
    name: 'sections',
    label: 'Onderdelen in het detailvenster',
    uitleg: 'Niets aangevinkt betekent alles.',
    selector: {
      select: {
        multiple: true,
        mode: 'list',
        options: SECTIES.map(function (s) {
          return { value: s.key, label: s.label };
        }),
      },
    },
  },
  {
    name: 'title',
    label: 'Kop boven de kaart',
    uitleg: 'Leeg laten als je er geen wilt.',
    selector: { text: {} },
  },
];

const EDITOR_STIJL = `
  .eigen { display: flex; flex-direction: column; padding: 8px 0; }
  .eigen > * + * { margin-top: 14px; }
  .eigen label { display: flex; flex-direction: column; font-size: 14px; }
  .eigen label > * + * { margin-top: 4px; }
  .eigen .uitleg { font-size: 12px; opacity: .6; }
  .eigen .schakel { flex-direction: row; align-items: center; }
  .eigen .schakel > * + * { margin-left: 10px; }
  .eigen input[type="text"] {
    padding: 8px; border-radius: 8px; border: 1px solid var(--divider-color, #444);
    background: var(--card-background-color, #1c1c1c); color: inherit; font: inherit;
  }
  .eigen .secties label { flex-direction: row; align-items: center; font-size: 13px; }
  .eigen .secties label > * + * { margin-left: 8px; }
  .eigen .secties label + label { margin-top: 2px; }
`;

class CyclingNextRaceCardEditor extends HTMLElement {
  setConfig(config) {
    const g = config || {};
    const view = g.view === 'countdown' ? 'countdown' : 'profile';
    this._config = {
      entity: 'sensor.cycling_next_race',
      view,
      design: 'default',
      visible_days: view === 'countdown' ? 0 : 2,
      details: true,
      sections: SECTIE_SLEUTELS.slice(),
      title: '',
      ...g,
    };
    if (g.always_show === true && g.visible_days === undefined) this._config.visible_days = 0;
    delete this._config.always_show;
    this._config.design = vormgeving(this._config.design);
    this._config.sections = secties(this._config.sections);
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    this._teken();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
    else this._teken();
  }

  /* Geef de nieuwe configuratie door aan Home Assistant.
   *
   * Twee sleutels gaan er eerst uit als ze niets toevoegen: alles
   * aangevinkt is hetzelfde als niets kiezen, en een lege kop is hetzelfde
   * als geen kop. Dat houdt de opgeslagen YAML kort, en belangrijker: een
   * kaart zonder `sections` toont ook onderdelen die er later bij komen.
   */
  _wijzig(config) {
    const schoon = { ...config };
    if (
      Array.isArray(schoon.sections) &&
      schoon.sections.length === SECTIE_SLEUTELS.length
    ) {
      delete schoon.sections;
    }
    if (!schoon.title) delete schoon.title;
    this._config = schoon;
    this.dispatchEvent(
      new CustomEvent('config-changed', {
        detail: { config: schoon },
        bubbles: true,
        composed: true,
      })
    );
  }

  _teken() {
    if (!this.shadowRoot || !this._config) return;

    if (customElements.get('ha-form')) {
      if (this._form) return; // al opgebouwd; alleen data bijwerken
      const form = document.createElement('ha-form');
      form.hass = this._hass;
      form.data = this._config;
      form.schema = VELDEN.map(({ name, selector }) => ({ name, selector }));
      form.computeLabel = (veld) =>
        (VELDEN.find((v) => v.name === veld.name) || {}).label || veld.name;
      form.computeHelper = (veld) =>
        (VELDEN.find((v) => v.name === veld.name) || {}).uitleg || '';
      form.addEventListener('value-changed', (e) => {
        e.stopPropagation();
        this._wijzig({ type: 'custom:cycling-next-race-card', ...e.detail.value });
      });
      this.shadowRoot.innerHTML = '';
      this.shadowRoot.appendChild(form);
      this._form = form;
      return;
    }

    // Terugval zonder ha-form. In Home Assistant is dat element er altijd;
    // dit is het vangnet voor het geval het ooit hernoemd wordt, want zonder
    // editor is de kaart alleen nog in YAML in te stellen.
    const c = this._config;
    const stijl = document.createElement('style');
    stijl.textContent = EDITOR_STIJL;
    const doos = document.createElement('div');
    doos.className = 'eigen';
    const keuze = (lijst, huidig) =>
      lijst
        .map(
          (o) =>
            `<option value="${esc(o.value)}"${o.value === huidig ? ' selected' : ''}>${esc(o.label)}</option>`
        )
        .join('');
    doos.innerHTML = `
      <label>Sensor<span class="uitleg">De sensor van Cycling Next Race.</span>
        <input type="text" name="entity" value="${esc(c.entity)}"></label>
      <label>Weergave<span class="uitleg">Hoogteprofiel of een regel met het aftellen.</span>
        <select name="view">
          <option value="profile"${c.view !== 'countdown' ? ' selected' : ''}>Hoogteprofiel</option>
          <option value="countdown"${c.view === 'countdown' ? ' selected' : ''}>Aftellen</option>
        </select></label>
      <label>Vormgeving<span class="uitleg">Eigen opmaak, het Home Assistant-thema of de Bubble-stijl.</span>
        <select name="design">${keuze(VORMGEVING, c.design)}</select></label>
      <label>Tonen vanaf (dagen voor de koers)
        <span class="uitleg">2 is vandaag en morgen, 7 is de hele week vooruit, 0 is altijd.</span>
        <input type="number" name="visible_days" min="0" max="60" value="${Number(c.visible_days) || 0}"></label>
      <label class="schakel"><input type="checkbox" name="details" ${c.details ? 'checked' : ''}>
        Detailvenster bij aantikken</label>
      <div class="secties">Onderdelen in het detailvenster
        <span class="uitleg">Niets aangevinkt betekent alles.</span>
        ${SECTIES.map(
          (s) =>
            `<label><input type="checkbox" name="sections" value="${esc(s.key)}"` +
            `${c.sections.indexOf(s.key) >= 0 ? ' checked' : ''}>${esc(s.label)}</label>`
        ).join('')}
      </div>
      <label>Kop boven de kaart<span class="uitleg">Leeg laten als je er geen wilt.</span>
        <input type="text" name="title" value="${esc(c.title)}"></label>
    `;
    doos.addEventListener('change', () => {
      const lees = (n) => doos.querySelector(`[name="${n}"]`);
      const aangevinkt = [];
      const vakjes = doos.querySelectorAll('[name="sections"]');
      for (let i = 0; i < vakjes.length; i++) {
        if (vakjes[i].checked) aangevinkt.push(vakjes[i].value);
      }
      this._wijzig({
        type: 'custom:cycling-next-race-card',
        entity: lees('entity').value.trim() || 'sensor.cycling_next_race',
        view: lees('view').value,
        design: vormgeving(lees('design').value),
        visible_days: Math.max(0, parseInt(lees('visible_days').value, 10) || 0),
        details: lees('details').checked,
        sections: secties(aangevinkt),
        title: lees('title').value.trim(),
      });
    });
    this.shadowRoot.innerHTML = '';
    this.shadowRoot.appendChild(stijl);
    this.shadowRoot.appendChild(doos);
  }
}

if (!customElements.get('cycling-next-race-card-editor')) {
  customElements.define('cycling-next-race-card-editor', CyclingNextRaceCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((k) => k.type === 'cycling-next-race-card')) {
  window.customCards.push({
  type: 'cycling-next-race-card',
  name: 'Cycling Next Race',
  description: 'Hoogteprofiel, cols en uitslagen van de eerstvolgende koers.',
  preview: false,
    documentationURL: 'https://github.com/vossov/cycling-next-race',
  });
}

console.info('%c CYCLING-NEXT-RACE-CARD ', 'background:#E4572E;color:#fff;border-radius:3px');
