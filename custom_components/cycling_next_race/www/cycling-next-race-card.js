/*
 * Cycling Next Race - Lovelace-kaart
 *
 * Wordt door de integratie zelf geregistreerd; je hoeft niets aan
 * resources of button_card_templates toe te voegen. Op je dashboard:
 *
 *   type: custom:cycling-next-race-card
 *
 * Opties:
 *   entity        standaard sensor.cycling_next_race
 *   details       true (standaard) opent bij een tik het volledige
 *                 overzicht; false laat de tegel alleen tonen
 *   always_show   false (standaard) verbergt de kaart als er de komende
 *                 dagen geen koers is; true toont hem altijd
 *
 * De hoogteprofielen komen uit dezelfde tekencode die eerder als
 * button-card-template werd meegeleverd.
 */

const CAT = { HC: '#E4572E', 1: '#F2A03D', 2: '#EBD24A', 3: '#7FB069', 4: '#5FA8A0' };

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

/** Uitslag of klassement op tijd (uitslag, algemeen, jongeren). */
function tijdlijst(titel, rijen, opties = {}) {
  if (!rijen || !rijen.length) return '';
  const regels = rijen
    .map((x, i) => {
      const tijd = i === 0 ? x.time || '' : gap(x.time, rijen[0].time);
      const extra = opties.verschillen
        ? beweging(x.move) + tijdwinst(x.gain_s)
        : '';
      return `<li><span class="pos">${esc(x.rank)}</span><span class="naam">${esc(x.rider)}</span><span class="wrd">${esc(tijd)}${extra}</span></li>`;
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
      return `<li><span class="pos">${esc(x.rank)}</span><span class="naam">${esc(x.rider)}</span><span class="wrd">${esc(x.points)}${beweging(x.move)}${winst}</span></li>`;
    })
    .join('');
  return `<section><h3>${esc(titel)}</h3><ol>${regels}</ol></section>`;
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

  dialog {
    border: none; border-radius: 22px; padding: 0; max-width: 560px; width: 92vw;
    max-height: 86vh; overflow: auto;
    background: var(--card-background-color, #1c1c1c);
    color: var(--primary-text-color, #e8eef4);
  }
  dialog::backdrop { background: rgba(0, 0, 0, .55); }
  .kop {
    display: flex; align-items: center; gap: 10px;
    padding: 14px 18px 6px; font-size: 17px; font-weight: 700;
  }
  .kop .sluit {
    margin-left: auto; cursor: pointer; border: none; background: none;
    color: inherit; font-size: 22px; line-height: 1; padding: 4px 8px;
  }
  .inhoud { padding: 0 18px 18px; }

  section { margin-top: 14px; }
  h3 { margin: 0 0 6px; font-size: 14px; font-weight: 700; }
  ol { list-style: none; margin: 0; padding: 0; font-size: 13.5px; }
  li { display: flex; gap: 8px; padding: 2px 0; align-items: baseline; }
  .pos { width: 1.6em; text-align: right; opacity: .55; font-variant-numeric: tabular-nums; }
  .naam { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .wrd { font-variant-numeric: tabular-nums; opacity: .85; white-space: nowrap; }
  .mv { margin-left: 6px; font-size: 12px; }

  .zenders { text-align: right; font-size: 13px; padding: 6px 0 2px; opacity: .9; }
  .zender { white-space: nowrap; }
  .zenders img { height: 20px; width: auto; border-radius: 3px;
                 vertical-align: middle; margin-right: 5px; }
  .scheiding { opacity: .45; margin: 0 6px; }
`;

class CyclingNextRaceCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement('cycling-next-race-card-editor');
  }

  static getStubConfig() {
    return { entity: 'sensor.cycling_next_race' };
  }

  setConfig(config) {
    this._config = {
      entity: 'sensor.cycling_next_race',
      details: true,
      always_show: false,
      ...(config || {}),
    };
    this._vorigeStatus = null;
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
  }

  set hass(hass) {
    this._hass = hass;
    const st = hass && hass.states[this._config.entity];
    // alleen hertekenen als er echt iets veranderd is
    const stempel = st ? `${st.state}|${st.last_updated}` : 'weg';
    if (stempel === this._vorigeStatus) return;
    this._vorigeStatus = stempel;
    this._teken(st);
  }

  getCardSize() {
    return 3;
  }

  _teken(st) {
    const root = this.shadowRoot;
    if (!st) {
      root.innerHTML = `<style>${STIJL}</style><ha-card><div class="leeg">${esc(this._config.entity)} bestaat niet.</div></ha-card>`;
      return;
    }

    const a = st.attributes || {};
    const dagen = Number(a.days_until);
    const verbergen =
      !this._config.always_show && isFinite(dagen) && dagen >= 2;
    if (verbergen || a.show_state === 'Klaar') {
      root.innerHTML = '';
      this.style.display = 'none';
      return;
    }
    this.style.display = 'block';

    const klikbaar = this._config.details;
    root.innerHTML = `
      <style>${STIJL}</style>
      <ha-card class="${klikbaar ? 'klikbaar' : ''}">${svgTegel({ attributes: a })}</ha-card>
      ${klikbaar ? this._dialoog(a) : ''}
    `;

    if (klikbaar) {
      const dlg = root.querySelector('dialog');
      root.querySelector('ha-card').onclick = () => dlg.showModal();
      root.querySelector('.sluit').onclick = () => dlg.close();
      dlg.onclick = (e) => {
        if (e.target === dlg) dlg.close();
      };
    }
  }

  _dialoog(a) {
    const entity = { attributes: a };
    const komend = (a.upcoming || []).length
      ? `<section><h3>Komende dagen</h3>${svgKomend(entity)}</section>`
      : '';

    return `
      <dialog>
        <div class="kop">
          <span>${esc(a.race_name || 'Wielrennen')}</span>
          <button class="sluit" aria-label="Sluiten">&times;</button>
        </div>
        <div class="inhoud">
          ${svgDetail(entity)}
          ${zenders(a.channels_detail)}
          ${komend}
          ${tijdlijst(a.last_stage_label || 'Uitslag', a.last_result)}
          ${tijdlijst('Algemeen klassement', a.gc_top, { verschillen: true })}
          ${puntenlijst('Puntenklassement', a.points_top)}
          ${puntenlijst('Bergklassement', a.kom_top)}
          ${tijdlijst('Jongerenklassement', a.youth_top, { verschillen: true })}
          ${tijdlijst(a.other_label || '', a.other_result)}
        </div>
      </dialog>
    `;
  }
}

customElements.define('cycling-next-race-card', CyclingNextRaceCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'cycling-next-race-card',
  name: 'Cycling Next Race',
  description: 'Hoogteprofiel, cols en uitslagen van de eerstvolgende koers.',
  preview: false,
  documentationURL: 'https://github.com/vossov/cycling-next-race',
});

console.info('%c CYCLING-NEXT-RACE-CARD ', 'background:#E4572E;color:#fff;border-radius:3px');
