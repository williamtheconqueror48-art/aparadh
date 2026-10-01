/* APARADH — Crime in India 2024 explorer. Plain JS, no framework. */
"use strict";

const HEADS = [
  {key:"total",        label:"All cognizable crimes",      cat:"Overall", short:"All crimes"},
  {key:"ipc_bns",      label:"IPC / BNS offences",         cat:"Overall", short:"IPC/BNS"},
  {key:"sll",          label:"Special & Local Laws",       cat:"Overall", short:"SLL"},
  {key:"murder",       label:"Murder",                     cat:"Violent crime", short:"Murder"},
  {key:"kidnapping",   label:"Kidnapping & abduction",     cat:"Violent crime", short:"Kidnapping"},
  {key:"rioting",      label:"Rioting",                    cat:"Violent crime", short:"Rioting"},
  {key:"women",        label:"Crimes against women",       cat:"Women & children", short:"Vs women", women:true},
  {key:"rape",         label:"Rape",                       cat:"Women & children", short:"Rape", women:true, y2024:true},
  {key:"attempt_rape", label:"Attempt to commit rape",     cat:"Women & children", short:"Attempt rape", women:true, y2024:true},
  {key:"dowry_death",  label:"Dowry deaths",               cat:"Women & children", short:"Dowry deaths", women:true, y2024:true},
  {key:"cruelty",      label:"Cruelty by husband/relatives",cat:"Women & children", short:"Cruelty", women:true, y2024:true},
  {key:"children",     label:"Crimes against children",    cat:"Women & children", short:"Vs children", child:true},
  {key:"senior_citizens",label:"Crimes against senior citizens",cat:"Vulnerable groups", short:"Vs seniors", senior:true},
  {key:"sc",           label:"Crimes against Scheduled Castes",cat:"Vulnerable groups", short:"Vs SCs", sc:true},
  {key:"st",           label:"Crimes against Scheduled Tribes",cat:"Vulnerable groups", short:"Vs STs", st:true},
  {key:"theft",        label:"Theft",                      cat:"Property", short:"Theft", y2024:true},
  {key:"burglary",     label:"Burglary",                   cat:"Property", short:"Burglary", y2024:true},
  {key:"robbery",      label:"Robbery",                    cat:"Property", short:"Robbery", y2024:true},
  {key:"dacoity",      label:"Dacoity",                    cat:"Property", short:"Dacoity", y2024:true},
  {key:"extortion",    label:"Extortion",                  cat:"Property", short:"Extortion", y2024:true},
  {key:"cheating_fraud",label:"Cheating & fraud",          cat:"Property", short:"Cheating", y2024:true},
  {key:"economic",     label:"Economic offences",          cat:"White-collar & cyber", short:"Economic"},
  {key:"cyber",        label:"Cybercrime",                 cat:"White-collar & cyber", short:"Cyber"},
  {key:"against_state",label:"Offences against the state", cat:"White-collar & cyber", short:"Vs state"},
];

const BINS = ["#26241a","#4a3a22","#8a5a24","#c97a2c","#e8482f"];
const RATEBASE = h =>
  h.women ? "per lakh women" :
  h.child ? "per lakh children" :
  h.senior ? "per lakh senior citizens" :
  h.sc ? "per lakh SC population" :
  h.st ? "per lakh ST population" : "per lakh population";

const fmt = n => (n === null || n === undefined) ? "—" : Number(n).toLocaleString("en-IN");
const fmt1 = n => (n === null || n === undefined) ? "—" : Number(n).toFixed(1);
const headByKey = k => HEADS.find(h => h.key === k);

let DATA = null, MAPD = null;
const sel = { head: "total", state: null, sortKey: "total_rate", sortDir: -1 };
// shareable deep links: ?head=cyber&state=Rajasthan
try {
  const q = new URLSearchParams(location.search);
  if (q.get("head") && HEADS.some(h => h.key === q.get("head"))) sel.head = q.get("head");
  if (q.get("state")) sel.state = q.get("state");
} catch(e) {}

/* ---------- boot ---------- */
Promise.all([
  fetch("data/aparadh_2024.json").then(r => r.json()),
  fetch("data/india-map.json").then(r => r.json())
]).then(([d, m]) => {
  DATA = d; MAPD = m;
  renderNational(); renderHeadGroups(); renderMap(); renderPanel(); renderTable(); renderCoverage();
}).catch(e => {
  document.body.insertAdjacentHTML("afterbegin",
    `<div style="padding:20px;border:3px solid #e8482f;margin:20px">Data failed to load: ${e}</div>`);
});

/* ---------- national ---------- */
function renderNational(){
  const I = DATA.india;
  const t = I.total;
  const cards = [
    {tag:"THE HEADLINE", n: fmt(t.c2024), cap:"cognizable crimes registered in 2024", sub:`rate ${fmt1(t.rate_2024)} per lakh population`},
    {tag:"MURDER", n: fmt(I.murder.c2024), cap:"murders — down 2.4% from 2023", sub:`rate ${fmt1(I.murder.rate_2024)} per lakh`, accent:true},
    {tag:"VS WOMEN", n: fmt(I.women.c2024), cap:"crimes against women — down 1.5%", sub:`rate ${fmt1(I.women.rate_2024)} per lakh women`},
    {tag:"CYBERCRIME", n: fmt(I.cyber.c2024), cap:"cybercrimes — up 17.9%, fastest riser", sub:`rate ${fmt1(I.cyber.rate_2024)} per lakh`},
  ];
  document.getElementById("national-stats").innerHTML = cards.map(c =>
    `<div class="stat${c.accent?" accent":""}"><div class="micro">${c.tag}</div>
     <div class="num">${c.n}</div><div class="cap">${c.cap}<br>${c.sub}</div></div>`).join("");

  // trend sparkline 2022-2024
  const vals = [t.c2022, t.c2023, t.c2024], yrs = ["2022","2023","2024"];
  const W=460,H=150,P=34, mn=Math.min(...vals)*0.985, mx=Math.max(...vals)*1.005;
  const X=i=>P+i*(W-2*P)/2, Y=v=>H-P-(v-mn)/(mx-mn)*(H-2*P);
  const pts = vals.map((v,i)=>`${X(i)},${Y(v)}`).join(" ");
  document.getElementById("trend-spark").innerHTML =
    `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" role="img" aria-label="Trend of total crimes 2022 to 2024">
     <polyline points="${pts}" fill="none" stroke="#e8482f" stroke-width="4"/>
     ${vals.map((v,i)=>`<circle cx="${X(i)}" cy="${Y(v)}" r="6" fill="#f2ecdc"/>
       <text x="${X(i)}" y="${Y(v)-14}" text-anchor="middle" fill="#f2ecdc" font-size="17" font-weight="700" font-family="Zilla Slab,serif">${fmt(v)}</text>
       <text x="${X(i)}" y="${H-8}" text-anchor="middle" fill="#a89f86" font-size="14" font-weight="700" font-family="Zilla Slab,serif">${yrs[i]}</text>`).join("")}
    </svg>`;
  document.getElementById("trend-cap").textContent =
    `2022: ${fmt(vals[0])} · 2023: ${fmt(vals[1])} (peak) · 2024: ${fmt(vals[2])}. 2024 fell 5.7% from the 2023 peak.`;

  // movers
  const rows = HEADS.filter(h=>!h.y2024).map(h=>{
    const e = I[h.key];
    if(!e || e.c2023 == null) return null;
    const pc = (e.c2024 - e.c2023)/e.c2023*100;
    return {label:h.label, pc, c2024:e.c2024};
  }).filter(Boolean).sort((a,b)=>b.pc-a.pc);
  const up = rows.slice(0,2), dn = rows.slice(-2).reverse();
  document.getElementById("movers").innerHTML =
    [...up.map(r=>({...r,up:true})), ...dn.map(r=>({...r,up:false}))].map(r=>
    `<div class="sp-kv"><span class="k">${r.label}</span>
     <span style="color:${r.up?"#e8482f":"#f2ecdc"};font-weight:700">${r.up?"+":""}${r.pc.toFixed(1)}% <span class="mut" style="font-weight:400">· ${fmt(r.c2024)}</span></span></div>`).join("");
}

/* ---------- head selector ---------- */
function renderHeadGroups(){
  const cats = [...new Set(HEADS.map(h=>h.cat))];
  document.getElementById("head-groups").innerHTML = cats.map(c=>
    `<div class="head-cat micro">${c}</div><div class="head-btns">` +
    HEADS.filter(h=>h.cat===c).map(h=>
      `<button class="head-btn${h.key===sel.head?" active":""}" data-head="${h.key}" aria-pressed="${h.key===sel.head}">${h.short}</button>`).join("") +
    `</div>`).join("");
  document.querySelectorAll(".head-btn").forEach(b=>b.addEventListener("click",()=>{
    sel.head = b.dataset.head;
    document.querySelectorAll(".head-btn").forEach(x=>{
      x.classList.toggle("active", x===b); x.setAttribute("aria-pressed", x===b);
    });
    renderMap(); renderPanel();
  }));
}

/* ---------- map ---------- */
function quintiles(rates){
  const s=[...rates].sort((a,b)=>a-b);
  const q=p=>s[Math.min(s.length-1, Math.floor(p*s.length))];
  return [q(.2),q(.4),q(.6),q(.8)];
}
function binOf(v, br){ let b=0; for(const t of br){ if(v>t) b++; } return Math.min(4,b); }

function renderMap(){
  const H = headByKey(sel.head);
  const rates = DATA.states.map(s=>s.heads[sel.head].rate_2024);
  const br = quintiles(rates);
  const byName = Object.fromEntries(DATA.states.map(s=>[s.name, s.heads[sel.head]]));

  let svg = `<svg viewBox="${MAPD.viewBox}" role="img" aria-label="Map of India coloured by ${H.label} rate">`;
  for(const name of MAPD.names){
    const v = byName[name];
    const fill = v ? BINS[binOf(v.rate_2024, br)] : "#000";
    svg += `<path class="state-path${sel.state===name?" selected":""}" data-name="${name}" d="${MAPD.paths[name]}" fill="${fill}"><title>${name}</title></path>`;
  }
  for(const [name,[x,y]] of Object.entries(MAPD.markers)){
    const v = byName[name];
    const fill = v ? BINS[binOf(v.rate_2024, br)] : "#000";
    svg += `<circle class="ut-marker${sel.state===name?" selected":""}" data-name="${name}" cx="${x}" cy="${y}" r="10" fill="${fill}"><title>${name}</title></circle>`;
  }
  svg += `<path class="map-outline" d="${MAPD.outer}"/></svg>`;
  document.getElementById("map-holder").innerHTML = svg;

  // legend: low/high anchors + overall range
  const lo = Math.min(...rates), hi = Math.max(...rates);
  document.getElementById("map-legend").innerHTML = BINS.map((c,i)=>
    `<span class="swatch" style="background:${c}">${i===0?"LOW":""}${i===4?"HIGH":""}</span>`).join("") +
    `<span class="swatch" style="background:transparent;color:#a89f86;text-shadow:none;border-left:2px solid #f2ecdc">rate ${fmt1(lo)} – ${fmt1(hi)}</span>`;
  document.getElementById("legend-ratebase").textContent = RATEBASE(H);

  const tip = document.getElementById("tooltip");
  const show = (el, ev)=>{
    const name = el.dataset.name, v = byName[name];
    tip.innerHTML = `<div class="tt-name">${name}</div>
      <div class="tt-row"><span>Cases (2024)</span><b>${fmt(v.c2024)}</b></div>
      <div class="tt-row"><span>Rate</span><b>${fmt1(v.rate_2024)}</b></div>
      <div class="tt-row"><span>${H.short}</span><b style="color:#e8482f">click →</b></div>`;
    tip.hidden = false; move(ev);
  };
  const move = ev=>{ tip.style.left = Math.min(innerWidth-270, ev.clientX+16)+"px"; tip.style.top = (ev.clientY+16)+"px"; };
  document.querySelectorAll(".state-path,.ut-marker").forEach(el=>{
    el.addEventListener("mousemove", ev=>show(el,ev));
    el.addEventListener("mouseleave", ()=>tip.hidden=true);
    el.addEventListener("click", ()=>{ sel.state = el.dataset.name; renderMap(); renderPanel();
      document.getElementById("explorer").scrollIntoView({behavior:"smooth", block:"nearest"}); });
  });
}

/* ---------- state panel ---------- */
function stateRank(key){
  const order=[...DATA.states].sort((a,b)=>b.heads[key].rate_2024-a.heads[key].rate_2024);
  const m={}; order.forEach((s,i)=>m[s.name]=i+1); return m;
}

function renderPanel(){
  const el = document.getElementById("state-panel");
  const H = headByKey(sel.head);
  if(!sel.state || !DATA.states.some(x=>x.name===sel.state)){
    const top=[...DATA.states].sort((a,b)=>b.heads[sel.head].rate_2024-a.heads[sel.head].rate_2024).slice(0,5);
    const bot=[...DATA.states].sort((a,b)=>a.heads[sel.head].rate_2024-b.heads[sel.head].rate_2024).slice(0,5);
    el.innerHTML = `<div class="sp-empty">← <b>Click any state or UT on the map</b><br>for its full crime profile.<br><br>
      <span class="micro">HIGHEST ${H.short.toUpperCase()} RATE</span></div>` +
      top.map(s=>`<div class="sp-kv"><span class="k">${s.name}</span><span><b>${fmt1(s.heads[sel.head].rate_2024)}</b></span></div>`).join("") +
      `<div class="micro" style="margin-top:14px">LOWEST ${H.short.toUpperCase()} RATE</div>` +
      bot.map(s=>`<div class="sp-kv"><span class="k">${s.name}</span><span><b>${fmt1(s.heads[sel.head].rate_2024)}</b></span></div>`).join("");
    return;
  }
  const s = DATA.states.find(x=>x.name===sel.state);
  const v = s.heads[sel.head];
  const rank = stateRank(sel.head)[s.name];
  const rb = RATEBASE(H);

  let trend = "";
  if(!H.y2024 && v.c2022!=null){
    const vals=[v.c2022,v.c2023,v.c2024], mx=Math.max(...vals,1);
    trend = `<div class="micro" style="margin-top:14px">REGISTERED CASES · 2022–2024</div><div class="trendbar-wrap"><div class="trendbar">`+
      vals.map((n,i)=>`<div class="tbar${i===2?" cur":""}" style="height:${Math.max(6,n/mx*100)}%" title="${["2022","2023","2024"][i]}: ${fmt(n)}"><span>${["22","23","24"][i]}</span></div>`).join("")+
      `</div><div class="fine mut">${fmt(vals[0])} → ${fmt(vals[2])} (${vals[0]?(((vals[2]-vals[0])/vals[0]*100).toFixed(1)):"—"}% over 2 yrs)</div></div>`;
  } else if(v.ipc_2024!=null){
    const tot=v.ipc_2024+v.bns_2024||1;
    trend = `<div class="micro" style="margin-top:14px">2024: OLD IPC vs NEW BNS CODE</div>
      <div class="splitbar"><div class="ipc" style="width:${v.ipc_2024/tot*100}%"></div><div class="bns" style="width:${v.bns_2024/tot*100}%"></div></div>
      <div class="split-legend"><span><i style="background:#8a5a24"></i>IPC ${fmt(v.ipc_2024)}</span><span><i style="background:#e8482f"></i>BNS ${fmt(v.bns_2024)}</span></div>
      <div class="fine mut">2024 straddles two criminal codes — cases were still being registered under the old IPC alongside the new Bharatiya Nyaya Sanhita.</div>`;
  }

  const allRows = HEADS.map(h=>{
    const e=s.heads[h.key];
    return `<tr class="${h.key===sel.head?"cur":""}"><td>${h.label}</td><td class="n">${fmt(e.c2024)}</td><td class="n">${fmt1(e.rate_2024)}</td></tr>`;
  }).join("");

  el.innerHTML = `
    <div class="micro">${H.cat.toUpperCase()} · ${s.type==="UT"?"UNION TERRITORY":"STATE"}</div>
    <div class="sp-name">${s.name}</div>
    <div class="sp-meta">Population (projected, mid-2024): <b>${fmt(s.pop_lakh_2024)} lakh</b></div>
    <div class="sp-head"><div class="micro">${H.label.toUpperCase()} · 2024</div>
      <div class="sp-big">${fmt(v.c2024)} <small>cases</small></div>
      <div class="sp-kv"><span class="k">Rate (${rb})</span><span><b>${fmt1(v.rate_2024)}</b></span></div>
      <div class="sp-kv"><span class="k">All-India rank (by rate)</span><span><b>#${rank}</b> of 36</span></div>
      <div class="sp-kv"><span class="k">NCRB table</span><span>${DATA.heads[H.key].table}</span></div>
    </div>
    ${trend}
    <div class="sp-allheads"><div class="micro" style="margin-bottom:8px">ALL 24 HEADS · ${s.name.toUpperCase()} · 2024</div>
      <table><thead><tr><th>Crime head</th><th class="n">Cases</th><th class="n">Rate</th></tr></thead>
      <tbody>${allRows}</tbody></table></div>`;
}

/* ---------- table ---------- */
const TCOLS = [
  {k:"name", l:"State / UT", num:false},
  {k:"type", l:"Type", num:false},
  {k:"pop_lakh_2024", l:"Pop. (lakh)", num:true},
  {k:"total", l:"Total cases", num:true, head:"total", f:"c2024"},
  {k:"total_rate", l:"Total rate", num:true, head:"total", f:"rate_2024"},
  {k:"murder", l:"Murder", num:true, head:"murder", f:"c2024"},
  {k:"murder_rate", l:"Murder rate", num:true, head:"murder", f:"rate_2024"},
  {k:"women", l:"Vs women", num:true, head:"women", f:"c2024"},
  {k:"women_rate", l:"Vs women rate", num:true, head:"women", f:"rate_2024"},
  {k:"cyber", l:"Cybercrime", num:true, head:"cyber", f:"c2024"},
];
function cellVal(s, c){
  if(c.head) { const v=s.heads[c.head][c.f]; return v; }
  return s[c.k];
}
function renderTable(){
  const q = (document.getElementById("state-search").value||"").toLowerCase();
  let rows = DATA.states.filter(s=>s.name.toLowerCase().includes(q));
  const col = TCOLS.find(c=>c.k===sel.sortKey);
  rows.sort((a,b)=>{
    let x=cellVal(a,col), y=cellVal(b,col);
    if(typeof x==="string") return sel.sortDir*x.localeCompare(y);
    return sel.sortDir*((x??-1)-(y??-1));
  });
  const arrow = k=>k===sel.sortKey?`<span class="arrow">${sel.sortDir===1?"▲":"▼"}</span>`:"";
  document.getElementById("states-table").innerHTML =
    `<thead><tr>${TCOLS.map(c=>`<th data-k="${c.k}" class="${c.num?"n":""}">${c.l} ${arrow(c.k)}</th>`).join("")}</tr></thead>
     <tbody>${rows.map(s=>`<tr data-name="${s.name}" class="${sel.state===s.name?"selected":""}">
       ${TCOLS.map(c=>{const v=cellVal(s,c);
         return `<td class="${c.num?"n":""}">${typeof v==="string"?v:(c.k.startsWith("pop")?fmt(v):(c.k.endsWith("rate")?fmt1(v):fmt(v)))}</td>`;}).join("")}
     </tr>`).join("")}</tbody>`;
  document.querySelectorAll("#states-table th").forEach(th=>th.addEventListener("click",()=>{
    const k=th.dataset.k;
    if(sel.sortKey===k) sel.sortDir*=-1; else { sel.sortKey=k; sel.sortDir = (typeof cellVal(DATA.states[0],TCOLS.find(c=>c.k===k))==="string")?1:-1; }
    renderTable();
  }));
  document.querySelectorAll("#states-table tbody tr").forEach(tr=>tr.addEventListener("click",()=>{
    sel.state = tr.dataset.name; renderMap(); renderPanel(); renderTable();
    document.getElementById("explorer").scrollIntoView({behavior:"smooth"});
  }));
}
document.getElementById("state-search").addEventListener("input", renderTable);

/* ---------- coverage ---------- */
function renderCoverage(){
  const cats=[...new Set(HEADS.map(h=>h.cat))];
  document.getElementById("coverage-list").innerHTML =
    `<p><b>${HEADS.length} crime heads × 36 states/UTs = ${HEADS.length*36} verified figures.</b> Every figure was parsed from the NCRB PDFs and cross-checked: state rows sum to the NCRB's own TOTAL rows in every table — all checks passed, zero dropped.</p>`+
    cats.map(c=>`<p><b>${c}:</b> `+HEADS.filter(h=>h.cat===c).map(h=>`${h.label} <span class="mut">(${DATA.heads[h.key].table})</span>`).join(" · ")+`</p>`).join("")+
    `<p class="mut">Not yet parsed: the remaining ~90 minor IPC/BNS sub-heads of table 1A.4 (they use variable sub-column layouts — e.g. kidnapping sub-categories — and are not uniformly machine-readable). Nothing on this page is estimated or interpolated.</p>`;
}
