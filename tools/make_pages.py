#!/usr/bin/env python3
"""Emit the static HTML pages. Shared shell, per-page body + script. Run: python3 tools/make_pages.py"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SHELL = """<!doctype html>
<html lang="en-ZA" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · The Madlanga Tracker</title>
<meta name="description" content="__DESC__">
<meta name="colour-scheme" content="dark light">
<meta name="color-scheme" content="dark light">
<link rel="stylesheet" href="assets/css/app.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%230e1116'/><text x='16' y='23' font-size='19' font-family='monospace' text-anchor='middle' fill='%236ea8fe'>M</text></svg>">
</head>
<body>
<main class="wrap" id="main">__BODY__</main>
<script src="assets/js/core.js"></script>
__EXTRA__
<script>
MT.chrome();
__SCRIPT__
</script>
</body>
</html>
"""

def page(name, title, desc, body, script, extra=""):
    html = (SHELL.replace("__TITLE__", title).replace("__DESC__", desc)
                 .replace("__BODY__", body).replace("__SCRIPT__", script)
                 .replace("__EXTRA__", extra))
    with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
        f.write(html)
    print("  " + name)

PHASE_NOTICE = """
<div class="notice" id="phase-notice"><strong>Phase 1 — scaffold.</strong>
This site currently holds only the ten most recent sitting days as a working sample.
Days 1 to <span id="pn-first">…</span> are not yet back-filled. Nothing here is invented: every
claim carries a source and a tier, and everything that could not be verified is listed on the
<a href="methodology.html">Methodology</a> page.</div>"""

# ---------------------------------------------------------------- home
page("index.html", "Home", "This week's briefing on the Madlanga Commission of Inquiry.", """
<p class="stamp" id="stamp">Loading…</p>
""" + PHASE_NOTICE + """
<div id="brief"></div>
""", """
(async () => {
  const [meta, idx] = await Promise.all([MT.data('meta'), MT.briefing('index.json')]);
  document.getElementById('pn-first').textContent = (meta.latest_day - meta.days_in_data);
  document.getElementById('stamp').textContent =
    'Last updated ' + meta.last_updated + ' · most recent sitting ' + meta.latest_day_date +
    (meta.latest_day_verified ? ', Day ' + meta.latest_day : ', reported as Day ' + meta.latest_day +
     ' by broadcasters but not yet listed on the commission\\'s own index') +
    ' · ' + meta.days_in_data + ' sitting days in the data layer';

  if (!idx.length) { document.getElementById('brief').innerHTML = '<p class="empty">No briefing published yet.</p>'; return; }
  const b = await MT.briefing(idx[0].file);
  const link = (u) => `<a href="${MT.esc(u)}" target="_blank" rel="noopener noreferrer">${MT.esc(MT.host(u))}</a>`;

  document.getElementById('brief').innerHTML = `
    <h2 style="margin-top:8px">${MT.esc(b.title)}</h2>
    <p class="muted small mono">Published ${MT.esc(b.published)} · covers ${MT.esc(b.covers.from)} – ${MT.esc(b.covers.to)}</p>

    <div class="card"><h3 style="margin-top:0">In one line</h3><p class="lead">${MT.esc(b.in_one_line)}</p></div>

    <h2>What happened</h2>
    ${b.what_happened.map(d => `<article class="card">
      <div class="dayhead"><span class="num">Day ${d.day}</span><span class="date">${MT.esc(d.date)}</span></div>
      <h3 style="margin:4px 0 6px">${MT.esc(d.heading)}</h3>
      <p>${MT.esc(d.body)}</p>
      <p class="small muted">${MT.esc(d.tier_note)}</p>
      <p class="small">Sources: ${d.sources.map(link).join(' · ')}</p>
    </article>`).join('')}

    <h2>Why it matters</h2>
    <div class="card"><p class="small muted" style="margin-top:0">Analysis, clearly separated from the facts above.</p>
      ${b.why_it_matters.split('\\n\\n').map(p => `<p>${MT.esc(p)}</p>`).join('')}</div>

    ${b.aside ? `<p class="aside-joke">${MT.esc(b.aside)}</p>` : ''}

    <h2>Loose ends</h2>
    <div class="card"><ul class="tight">${b.loose_ends.map(x => `<li>${MT.esc(x)}</li>`).join('')}</ul></div>

    <h2>New faces</h2>
    <div class="card">${b.new_faces.map(n =>
      `<p style="margin:6px 0">${MT.statusPill(n.status)} <strong>${MT.esc(n.name)}</strong> — ${MT.esc(n.note)}</p>`).join('')}</div>

    <h2>Watch next week</h2>
    <div class="card"><ul class="tight">${b.watch_next_week.map(x => `<li>${MT.esc(x)}</li>`).join('')}</ul></div>

    <h2>Sources</h2>
    <div class="card">
      <p class="small muted" style="margin-top:0">${MT.esc(b.tier_summary)}</p>
      ${MT.sourceList(b.sources.map(s => ({...s, retrieved: '', partial: false})))}
    </div>`;
})().catch(e => document.getElementById('brief').innerHTML =
  '<p class="empty">Could not load the briefing: ' + MT.esc(e.message) + '</p>');
""")

# ---------------------------------------------------------------- archive
page("archive.html", "Archive", "Every past weekly briefing, by date.", """
<h2 style="margin-top:0">Briefing archive</h2>
<p class="lead">Every weekly briefing, newest first. Each is archived as JSON under <span class="mono">/briefings/</span>.</p>
<div id="list"></div>
""", """
(async () => {
  const idx = await MT.briefing('index.json');
  const el = document.getElementById('list');
  if (!idx.length) { el.innerHTML = '<p class="empty">Nothing archived yet.</p>'; return; }
  el.innerHTML = idx.map(b => `<article class="card">
    <div class="dayhead"><span class="date">${MT.esc(b.published)}</span>
      ${MT.tierBadge(b.highest_tier)}<span class="small muted">${b.words} words · Days ${b.covers.days.join(', ')}</span></div>
    <h3 style="margin:2px 0 6px"><a href="index.html">${MT.esc(b.title)}</a></h3>
    <p>${MT.esc(b.in_one_line)}</p>
    <p class="small"><a href="briefings/${MT.esc(b.file)}" target="_blank" rel="noopener">Raw JSON</a></p>
  </article>`).join('');
})().catch(e => document.getElementById('list').innerHTML = '<p class="empty">' + MT.esc(e.message) + '</p>');
""")

# ---------------------------------------------------------------- hearing days
page("days.html", "Hearing days", "Every sitting day of the commission, filterable.", """
<h2 style="margin-top:0">Hearing days</h2>
<p class="lead" id="intro">Loading…</p>
<div class="controls">
  <input type="search" id="q" placeholder="Search witness, summary, ruling, exhibit…" aria-label="Search hearing days">
  <label class="ctl">From <input type="date" id="from" title="Date filter uses your browser locale; the site displays YYYY/MM/DD"></label>
  <label class="ctl">To <input type="date" id="to"></label>
  <button class="chip" id="clear" type="button">Clear</button>
</div>
<div class="controls" id="ws-filter"></div>
<p class="small muted" id="count"></p>
<div id="list"></div>
""", """
let DAYS = [], META = null, WS = new Set();

function render() {
  const q = document.getElementById('q').value.trim().toLowerCase();
  const f = document.getElementById('from').value.replace(/-/g, '/');
  const t = document.getElementById('to').value.replace(/-/g, '/');
  const out = DAYS.filter(d => {
    if (WS.size && !WS.has(d.workstream)) return false;
    if (f && d.date < f) return false;
    if (t && d.date > t) return false;
    if (!q) return true;
    const hay = [d.summary, d.date, 'day ' + d.day_number,
      ...d.witnesses.map(w => w.name + ' ' + (w.role_as_described || '')),
      ...d.rulings.map(r => r.description),
      ...d.exhibits.map(e => (e.ref || '') + ' ' + e.description),
      ...d.quotes.map(x => x.text + ' ' + x.speaker)].join(' ').toLowerCase();
    return hay.includes(q);
  });
  document.getElementById('count').textContent =
    out.length + ' of ' + DAYS.length + ' sitting days shown';
  document.getElementById('list').innerHTML = out.length
    ? out.map(d => MT.dayCard(d, META)).join('')
    : '<p class="empty">No sitting day matches those filters.</p>';
}

(async () => {
  [META, DAYS] = await MT.all('meta', 'days');
  document.getElementById('intro').innerHTML =
    'Day ' + META.latest_day + ' sat on ' + META.latest_day_date + '. This scaffold holds <strong>' +
    META.days_in_data + '</strong> of them — the most recent ten. <strong>' + META.days_outstanding +
    '</strong> earlier sitting days are not yet back-filled.';
  document.getElementById('ws-filter').innerHTML =
    '<span class="small muted">Workstream:</span>' + META.workstreams.map(w =>
      `<button class="chip" data-ws="${w.id}" aria-pressed="false"><span class="ws-dot" style="background:${w.colour}"></span>${MT.esc(w.label)}</button>`).join('');
  document.getElementById('ws-filter').addEventListener('click', ev => {
    const b = ev.target.closest('[data-ws]'); if (!b) return;
    const on = b.getAttribute('aria-pressed') === 'true';
    b.setAttribute('aria-pressed', String(!on));
    on ? WS.delete(b.dataset.ws) : WS.add(b.dataset.ws);
    render();
  });
  for (const id of ['q', 'from', 'to']) document.getElementById(id).addEventListener('input', render);
  document.getElementById('clear').addEventListener('click', () => {
    document.getElementById('q').value = ''; document.getElementById('from').value = '';
    document.getElementById('to').value = ''; WS.clear();
    document.querySelectorAll('[data-ws]').forEach(b => b.setAttribute('aria-pressed', 'false'));
    render();
  });
  const jump = new URLSearchParams(location.search).get('day');
  render();
  if (jump) { const t = document.getElementById('day-' + jump); if (t) t.scrollIntoView(); }
})().catch(e => document.getElementById('list').innerHTML = '<p class="empty">' + MT.esc(e.message) + '</p>');
""")

# ---------------------------------------------------------------- people
page("people.html", "People", "Everyone before the commission, with a visible status label.", """
<h2 style="margin-top:0">People</h2>
<p class="lead">Every named person carries a status label. <strong>This is a commission of inquiry, not a
criminal trial</strong> — none of these people is an accused before this commission, and no label here is a finding of
guilt. Where someone faces criminal proceedings in a separate matter, that is stated as such.</p>
<div class="controls">
  <input type="search" id="q" placeholder="Search name or role…" aria-label="Search people">
  <button class="chip" id="clear" type="button">Clear</button>
</div>
<div class="controls" id="st-filter"></div>
<p class="small muted" id="count"></p>
<div class="people-grid" id="grid"></div>
""", """
let PEOPLE = [], ST = new Set();

function render() {
  const q = document.getElementById('q').value.trim().toLowerCase();
  const out = PEOPLE.filter(p => {
    if (ST.size && !ST.has(p.status)) return false;
    if (!q) return true;
    return (p.name + ' ' + (p.role || '') + ' ' + (p.bio || '')).toLowerCase().includes(q);
  });
  document.getElementById('count').textContent = out.length + ' of ' + PEOPLE.length + ' people shown';
  document.getElementById('grid').innerHTML = out.length ? out.map(p => `
    <a class="card pcard" href="person.html?id=${encodeURIComponent(p.id)}">
      ${MT.avatar(p)}
      <div>
        <div class="nm">${MT.esc(p.name)}</div>
        <div class="rl">${MT.esc(p.role || '')}</div>
        ${MT.statusPill(p.status)}
        ${p.linked_days.length ? `<div class="small muted" style="margin-top:6px">Days ${p.linked_days.join(', ')}</div>` : ''}
      </div>
    </a>`).join('') : '<p class="empty">Nobody matches those filters.</p>';
}

(async () => {
  const [meta, people] = await MT.all('meta', 'people');
  PEOPLE = people;
  const counts = {};
  people.forEach(p => counts[p.status] = (counts[p.status] || 0) + 1);
  document.getElementById('st-filter').innerHTML = '<span class="small muted">Status:</span>' +
    meta.status_labels.map(s => `<button class="chip" data-st="${MT.esc(s)}" aria-pressed="false">${MT.esc(s)} (${counts[s] || 0})</button>`).join('');
  document.getElementById('st-filter').addEventListener('click', ev => {
    const b = ev.target.closest('[data-st]'); if (!b) return;
    const on = b.getAttribute('aria-pressed') === 'true';
    b.setAttribute('aria-pressed', String(!on));
    on ? ST.delete(b.dataset.st) : ST.add(b.dataset.st);
    render();
  });
  document.getElementById('q').addEventListener('input', render);
  document.getElementById('clear').addEventListener('click', () => {
    document.getElementById('q').value = ''; ST.clear();
    document.querySelectorAll('[data-st]').forEach(b => b.setAttribute('aria-pressed', 'false'));
    render();
  });
  render();
})().catch(e => document.getElementById('grid').innerHTML = '<p class="empty">' + MT.esc(e.message) + '</p>');
""")

# ---------------------------------------------------------------- entities
page("entities.html", "Entities", "Every company, unit or organisation named in the commission's evidence, who is linked to it and what is known about the money involved.", """
<h2 style="margin-top:0">Entities</h2>
<p class="lead">Every company, SAPS/TMPD unit, government body or other organisation named in the
evidence before the commission — what is alleged or established to have happened to it, who is
linked to it, and any rand figures the record itself puts on the matter. <strong>This is a
commission of inquiry, not a criminal trial</strong>: an entity appearing here is not a finding
against it, and a linked person is not thereby an accused. Money figures are pulled directly from
sourced descriptions and edges already in the data layer — nothing here is a new calculation or a
verified total, only what the record itself states. See <a href="methodology.html">Methodology</a>.</p>
<div class="controls">
  <input type="search" id="q" placeholder="Search entity, type or description…" aria-label="Search entities">
  <label class="ctl"><input type="checkbox" id="only-value"> Only entities with a rand figure</label>
  <select id="sort" aria-label="Sort entities">
    <option value="value">Sort: largest figure first</option>
    <option value="name">Sort: name (A–Z)</option>
    <option value="links">Sort: most linked people first</option>
  </select>
  <button class="chip" id="clear" type="button">Clear</button>
</div>
<p class="small muted" id="count"></p>
<div id="list"></div>
""", """
let ORGS = [], PEOPLE = {}, EVENTS = [], EDGES = [], BY_ORG = {};

// Pull rand figures out of free text without inventing anything — every match is a substring
// of a sourced description or edge that already exists in the data layer.
const RAND_RE = /R\\s?[\\d][\\d,\\.]*[\\s-]?(?:thousand|million|billion|bn|m|k)?\\b/gi;
const MULT = { thousand: 1e3, k: 1e3, million: 1e6, m: 1e6, billion: 1e9, bn: 1e9 };
function randFigures(text) {
  if (!text) return [];
  const out = [];
  for (const m of text.matchAll(RAND_RE)) {
    const raw = m[0].replace(/-$/, '').replace(/-/g, ' ').trim();
    const numPart = raw.replace(/^R\\s?/i, '').replace(/[a-z]+$/i, '').replace(/[,\\s-]+$/, '').replace(/,/g, '').trim();
    const num = parseFloat(numPart);
    if (Number.isNaN(num)) continue;
    const suffix = (raw.match(/[a-z]+$/i) || [''])[0].toLowerCase();
    // skip a bare number ("R360") when a longer match with a multiplier for the same
    // figure is already present ("R360 million") -- keep the more informative one only
    out.push({ text: raw, value: num * (MULT[suffix] || 1), bare: !suffix, num });
  }
  const withSuffix = new Set(out.filter(f => !f.bare).map(f => f.num));
  return out.filter(f => !(f.bare && withSuffix.has(f.num)));
}
function fmtRand(n) {
  if (n >= 1e9) return 'R' + (n / 1e9).toFixed(n % 1e9 ? 1 : 0) + 'bn';
  if (n >= 1e6) return 'R' + (n / 1e6).toFixed(n % 1e6 ? 1 : 0) + 'm';
  if (n >= 1e3) return 'R' + (n / 1e3).toFixed(0) + 'k';
  return 'R' + n.toLocaleString('en-ZA');
}

function render() {
  const q = document.getElementById('q').value.trim().toLowerCase();
  const onlyValue = document.getElementById('only-value').checked;
  const sort = document.getElementById('sort').value;

  let out = ORGS.filter(o => {
    if (onlyValue && !o._maxValue) return false;
    if (!q) return true;
    return (o.name + ' ' + (o.type || '') + ' ' + (o.description || '')).toLowerCase().includes(q);
  });
  out = out.slice().sort((a, b) => {
    if (sort === 'name') return a.name.localeCompare(b.name);
    if (sort === 'links') return b._links.length - a._links.length;
    return (b._maxValue || 0) - (a._maxValue || 0);
  });

  document.getElementById('count').textContent = out.length + ' of ' + ORGS.length + ' entities shown';
  document.getElementById('list').innerHTML = out.length ? out.map(o => `
    <div class="card">
      <div class="dayhead"><span style="font-weight:600;font-size:1.05em">${MT.esc(o.name)}</span>
        ${o.type ? '<span class="small muted">' + MT.esc(o.type) + '</span>' : ''}</div>
      ${o._figures.length ? `<p style="margin:6px 0">${o._figures.slice(0, 6).map(f =>
        `<span class="badge lbl-EVIDENCE" title="As stated in the record — not a verified total">${MT.esc(f.text)}</span>`).join(' ')}</p>` : ''}
      <p>${MT.esc(o.description || 'No description recorded yet.')}</p>
      ${o._links.length ? `<p class="small" style="margin:8px 0 0"><strong>Linked people:</strong> ${o._links.map(l =>
        `<a href="person.html?id=${encodeURIComponent(l.id)}">${MT.esc(l.name)}</a> <span class="muted">(${MT.esc(l.type)})</span>`).join(', ')}</p>`
        : '<p class="small muted" style="margin:8px 0 0">No person-to-entity relationship recorded yet in the map data.</p>'}
      <details><summary>Sources (${(o.sources || []).length})</summary>${MT.sourceList(o.sources || [])}</details>
    </div>`).join('') : '<p class="empty">No entity matches those filters.</p>';
}

(async () => {
  [PEOPLE, ORGS, EVENTS, EDGES] = await MT.all('people', 'orgs', 'events', 'edges');
  const nameOf = {}; PEOPLE.forEach(p => nameOf[p.id] = p.name);
  ORGS.forEach(o => nameOf[o.id] = o.name);

  ORGS.forEach(o => {
    const rel = EDGES.filter(e => e.from === o.id || e.to === o.id);
    const links = rel.map(e => {
      const otherId = e.from === o.id ? e.to : e.from;
      return { id: otherId, name: nameOf[otherId] || otherId, type: e.type || e.strength };
    }).filter(l => nameOf[l.id]);
    const seen = new Set();
    o._links = links.filter(l => (seen.has(l.id) ? false : (seen.add(l.id), true)));

    const figText = [o.description || '', ...rel.map(e => e.type || '')].join(' . ');
    const figs = randFigures(figText);
    const dedup = {}; figs.forEach(f => { if (!(f.text in dedup) || f.value > dedup[f.text].value) dedup[f.text] = f; });
    o._figures = Object.values(dedup).sort((a, b) => b.value - a.value);
    o._maxValue = o._figures.length ? o._figures[0].value : 0;
  });

  document.getElementById('q').addEventListener('input', render);
  document.getElementById('only-value').addEventListener('change', render);
  document.getElementById('sort').addEventListener('change', render);
  document.getElementById('clear').addEventListener('click', () => {
    document.getElementById('q').value = ''; document.getElementById('only-value').checked = false;
    document.getElementById('sort').value = 'value'; render();
  });
  render();
})().catch(e => document.getElementById('list').innerHTML = '<p class="empty">' + MT.esc(e.message) + '</p>');
""")

# ---------------------------------------------------------------- person profile
page("person.html", "Profile", "Profile and ego-network for one person before the commission.", """
<div id="profile"><p class="empty">Loading…</p></div>
<h2>Ego network</h2>
<p class="small muted" id="ego-note"></p>
<div id="graph-wrap"><svg id="graph"></svg>
  <div class="ghint">Drag to pan · scroll to zoom · click an edge for its sources</div>
  <div class="gpanel" id="panel"></div></div>
<div class="legend" id="legend"></div>
""", """
(async () => {
  const id = new URLSearchParams(location.search).get('id');
  const [meta, people, orgs, events, edges, days] = await MT.all('meta','people','orgs','events','edges','days');
  const p = people.find(x => x.id === id);
  const box = document.getElementById('profile');
  if (!p) { box.innerHTML = '<p class="empty">No such person in the data layer. <a href="people.html">Back to People</a></p>'; return; }
  document.title = p.name + ' · The Madlanga Tracker';

  const dayLinks = p.linked_days.map(n => `<a href="days.html?day=${n}#day-${n}">Day ${n}</a>`).join(', ');
  box.innerHTML = `
    <div class="card pcard" style="align-items:center">
      ${MT.avatar(p)}
      <div><h2 style="margin:0 0 4px">${MT.esc(p.name)}</h2>
        <div class="rl muted">${MT.esc(p.role || '')}</div>
        <div style="margin-top:6px">${MT.statusPill(p.status)}</div></div>
    </div>
    <div class="card">
      <p class="small muted" style="margin-top:0">Why this label: ${MT.esc(p.status_reason || 'Not recorded.')}</p>
      ${p.bio ? `<p>${MT.esc(p.bio)}</p>` : '<p class="muted">No biography assembled yet.</p>'}
      <p class="small">${p.first_appearance ? 'First appearance on record: <span class="mono">' + MT.esc(p.first_appearance) + '</span>. ' : ''}
      ${dayLinks ? 'Sitting days in this data layer: ' + dayLinks + '.' : 'No sitting day in this sample.'}</p>
      <p class="small muted">Photograph: ${p.photo_url ? MT.esc(p.photo_licence || 'licence not recorded') + ' — <a href="' + MT.esc(p.photo_source) + '" target="_blank" rel="noopener">source</a>' : 'none found under a reusable licence; an initials avatar is shown instead.'}</p>
      ${p.unverified.length ? `<details><summary>Not verified (${p.unverified.length})</summary><ul class="tight small muted">${p.unverified.map(u => `<li>${MT.esc(u)}</li>`).join('')}</ul></details>` : ''}
      <details><summary>Sources (${p.sources.length})</summary>${MT.sourceList(p.sources)}</details>
    </div>`;

  // ego network: this person + one hop
  const label = {}; const kind = {};
  people.forEach(x => { label[x.id] = x.name; kind[x.id] = 'person'; });
  orgs.forEach(x => { label[x.id] = x.name; kind[x.id] = 'org'; });
  events.forEach(x => { label[x.id] = x.title; kind[x.id] = 'event'; });

  const mine = edges.filter(e => e.from === id || e.to === id);
  const ids = new Set([id]); mine.forEach(e => { ids.add(e.from); ids.add(e.to); });
  document.getElementById('ego-note').textContent =
    mine.length + ' recorded relationship(s), ' + (ids.size - 1) + ' connected node(s). Every edge is sourced.';

  const COL = { person: '#6ea8fe', org: '#b58cf0', event: '#c9a227' };
  const nodeData = [...ids].filter(x => label[x]).map(x => ({
    id: x, label: label[x], kind: kind[x] || 'person',
    colour: x === id ? '#e2725b' : COL[kind[x]] || COL.person }));

  const svg = document.getElementById('graph');
  const panel = document.getElementById('panel');
  const g = ForceGraph(svg, {
    charge: -1100,
    onLink: (l, s, t) => {
      panel.classList.add('on');
      panel.innerHTML = `<button class="x" onclick="this.parentNode.classList.remove('on')">×</button>
        <p style="margin:0 0 6px"><strong>${MT.esc(s.label)}</strong> → <strong>${MT.esc(t.label)}</strong></p>
        <p class="small">${MT.esc(l.type || '')} <span class="badge lbl-${l.strength === 'testified' ? 'EVIDENCE' : 'REPORTING'}">${MT.esc(l.strength)}</span>
        ${l.date ? '<span class="mono muted"> ' + MT.esc(l.date) + '</span>' : ''}</p>
        ${MT.sourceList(l.sources)}`;
    },
    onNode: (n) => { if (n.kind === 'person' && n.id !== id) location.href = 'person.html?id=' + encodeURIComponent(n.id); }
  });
  g.set(nodeData, mine);
  document.getElementById('legend').innerHTML = Object.entries(g.STRENGTH_STYLE).map(([k, v]) =>
    `<span><i class="swatch" style="background:${v.colour}"></i>${k}</span>`).join('') +
    '<span>● person</span><span>■ organisation</span><span>◆ event</span>';
})().catch(e => document.getElementById('profile').innerHTML = '<p class="empty">' + MT.esc(e.message) + '</p>');
""", '<script src="assets/js/graph.js"></script>')

# ---------------------------------------------------------------- map
page("map.html", "The Map", "Interactive force-directed map of people, organisations and events.", """
<h2 style="margin-top:0">The Map</h2>
<p class="lead">People, organisations and events, and the sourced relationships between them.
Every edge carries its citations — click one. The default view is filtered: an unfiltered hairball
tells you nothing, so <strong>alleged</strong> edges start hidden.</p>

<div class="controls">
  <label class="ctl">Focus on
    <select id="ego"><option value="">— everyone —</option></select>
  </label>
  <label class="ctl">Hops <select id="hops"><option value="1">1</option><option value="2">2</option></select></label>
  <label class="ctl">From <input type="date" id="from" title="Date filter uses your browser locale; the site displays YYYY/MM/DD"></label>
  <label class="ctl">To <input type="date" id="to"></label>
  <button class="chip" id="reset" type="button">Reset view</button>
</div>
<div class="controls" id="ws-filter"></div>
<div class="controls" id="strength-filter"></div>
<p class="small muted" id="count"></p>

<div id="graph-wrap"><svg id="graph"></svg>
  <div class="ghint">Drag to pan · scroll to zoom · drag a node · click an edge for sources</div>
  <div class="gpanel" id="panel"></div></div>
<div class="legend" id="legend"></div>
<p class="small muted" style="margin-top:14px">Node size reflects how many recorded relationships a person has in
this data layer — not importance, and certainly not culpability.</p>
""", """
let META, PEOPLE, ORGS, EVENTS, EDGES, G;
let SHOW = new Set(['testified', 'documented', 'denied']);   // 'alleged' off by default
let WS = new Set();
const LABEL = {}, KIND = {}, WSOF = {};

function build() {
  const ego = document.getElementById('ego').value;
  const hops = +document.getElementById('hops').value;
  const f = document.getElementById('from').value.replace(/-/g, '/');
  const t = document.getElementById('to').value.replace(/-/g, '/');

  let edges = EDGES.filter(e => SHOW.has(e.strength));
  if (f) edges = edges.filter(e => !e.date || e.date >= f);
  if (t) edges = edges.filter(e => !e.date || e.date <= t);
  if (WS.size) edges = edges.filter(e => WS.has(WSOF[e.from]) || WS.has(WSOF[e.to]));

  let ids;
  if (ego) {
    ids = new Set([ego]);
    for (let i = 0; i < hops; i++) {
      const add = [];
      edges.forEach(e => { if (ids.has(e.from)) add.push(e.to); if (ids.has(e.to)) add.push(e.from); });
      add.forEach(x => ids.add(x));
    }
    edges = edges.filter(e => ids.has(e.from) && ids.has(e.to));
  } else {
    ids = new Set(); edges.forEach(e => { ids.add(e.from); ids.add(e.to); });
  }

  const COL = { person: '#6ea8fe', org: '#b58cf0', event: '#c9a227' };
  const nodes = [...ids].filter(x => LABEL[x]).map(x => ({
    id: x, label: LABEL[x], kind: KIND[x],
    colour: x === ego ? '#e2725b' : (COL[KIND[x]] || COL.person) }));

  const r = G.set(nodes, edges);
  document.getElementById('count').textContent =
    r.nodes + ' nodes · ' + r.links + ' sourced relationships shown, of ' + EDGES.length + ' in the data layer' +
    (SHOW.has('alleged') ? '' : ' (alleged edges hidden)');
}

(async () => {
  [META, PEOPLE, ORGS, EVENTS, EDGES] = await MT.all('meta','people','orgs','events','edges');
  PEOPLE.forEach(x => { LABEL[x.id] = x.name; KIND[x.id] = 'person'; });
  ORGS.forEach(x => { LABEL[x.id] = x.name; KIND[x.id] = 'org'; });
  EVENTS.forEach(x => { LABEL[x.id] = x.title; KIND[x.id] = 'event'; });

  // crude workstream attribution: a node belongs to the workstreams of the days it appears on
  const days = await MT.data('days');
  days.forEach(d => d.witnesses.forEach(w => { WSOF[w.person_id] = d.workstream; }));

  const sel = document.getElementById('ego');
  PEOPLE.slice().sort((a,b) => a.name.localeCompare(b.name))
    .forEach(p => sel.insertAdjacentHTML('beforeend', `<option value="${MT.esc(p.id)}">${MT.esc(p.name)}</option>`));

  document.getElementById('ws-filter').innerHTML = '<span class="small muted">Workstream:</span>' +
    META.workstreams.map(w => `<button class="chip" data-ws="${w.id}" aria-pressed="false"><span class="ws-dot" style="background:${w.colour}"></span>${MT.esc(w.label)}</button>`).join('');

  const panel = document.getElementById('panel');
  G = ForceGraph(document.getElementById('graph'), {
    charge: -820,
    onLink: (l, s, t) => {
      panel.classList.add('on');
      panel.innerHTML = `<button class="x" type="button">×</button>
        <p style="margin:0 0 6px"><strong>${MT.esc(s.label)}</strong> → <strong>${MT.esc(t.label)}</strong></p>
        <p class="small">${MT.esc(l.type || '')}
          <span class="badge lbl-${l.strength === 'testified' ? 'EVIDENCE' : 'REPORTING'}">${MT.esc(l.strength)}</span>
          ${l.date ? '<span class="mono muted"> ' + MT.esc(l.date) + '</span>' : ''}</p>
        ${MT.sourceList(l.sources)}`;
      panel.querySelector('.x').onclick = () => panel.classList.remove('on');
    },
    onNode: (n) => {
      // Full relationship list for this node, independent of whatever the current
      // filters happen to show in the graph itself — the popup answers "how is this
      // person/entity linked to everyone else", not just what's on screen right now.
      const rel = EDGES.filter(e => e.from === n.id || e.to === n.id);
      const links = rel.map(e => {
        const otherId = e.from === n.id ? e.to : e.from;
        return { id: otherId, label: LABEL[otherId], kind: KIND[otherId],
                 type: e.type, strength: e.strength, date: e.date };
      }).filter(l => l.label);
      links.sort((a, b) => (a.label || '').localeCompare(b.label || ''));

      const person = n.kind === 'person' ? PEOPLE.find(p => p.id === n.id) : null;
      const rec = n.kind !== 'person' ? (ORGS.concat(EVENTS)).find(x => x.id === n.id) : null;
      const desc = person ? (person.status_reason || person.bio || '') : ((rec && rec.description) || '');

      panel.classList.add('on');
      panel.innerHTML = `
        <button class="x" type="button">×</button>
        <p style="margin:0 0 4px"><strong>${MT.esc(n.label)}</strong></p>
        ${person ? `<p style="margin:0 0 8px">${MT.statusPill(person.status)}</p>` : ''}
        <p class="small">${MT.esc(desc || 'No summary recorded yet.')}</p>
        ${person ? `<p class="small"><a href="person.html?id=${encodeURIComponent(n.id)}">View full profile →</a></p>` : ''}
        <p class="small muted" style="margin:10px 0 4px"><strong>Linked to (${links.length}):</strong></p>
        ${links.length ? `<ul class="tight small" style="max-height:220px;overflow-y:auto">${links.map(l => `<li>${
          l.kind === 'person' ? `<a href="person.html?id=${encodeURIComponent(l.id)}">${MT.esc(l.label)}</a>` : MT.esc(l.label)
        } <span class="muted">— ${MT.esc(l.type || '')}</span> <span class="badge lbl-${l.strength === 'testified' ? 'EVIDENCE' : 'REPORTING'}">${MT.esc(l.strength)}</span>${
          l.date ? ' <span class="mono muted">' + MT.esc(l.date) + '</span>' : ''}</li>`).join('')}</ul>`
          : '<p class="small muted">No recorded relationships yet.</p>'}
        ${person ? `<p class="small" style="margin-top:8px"><button class="chip" id="panel-focus" type="button">Focus map on this person</button></p>` : ''}
        ${!person ? MT.sourceList(rec ? rec.sources : []) : ''}`;
      panel.querySelector('.x').onclick = () => panel.classList.remove('on');
      const focusBtn = panel.querySelector('#panel-focus');
      if (focusBtn) focusBtn.onclick = () => { document.getElementById('ego').value = n.id; panel.classList.remove('on'); build(); };
    }
  });

  document.getElementById('strength-filter').innerHTML = '<span class="small muted">Edge strength:</span>' +
    META.edge_strengths.map(s => `<button class="chip" data-st="${s}" aria-pressed="${SHOW.has(s)}"><i class="swatch" style="background:${G.STRENGTH_STYLE[s].colour}"></i>${s}</button>`).join('');
  document.getElementById('strength-filter').addEventListener('click', ev => {
    const b = ev.target.closest('[data-st]'); if (!b) return;
    const on = b.getAttribute('aria-pressed') === 'true';
    b.setAttribute('aria-pressed', String(!on));
    on ? SHOW.delete(b.dataset.st) : SHOW.add(b.dataset.st);
    build();
  });
  document.getElementById('ws-filter').addEventListener('click', ev => {
    const b = ev.target.closest('[data-ws]'); if (!b) return;
    const on = b.getAttribute('aria-pressed') === 'true';
    b.setAttribute('aria-pressed', String(!on));
    on ? WS.delete(b.dataset.ws) : WS.add(b.dataset.ws);
    build();
  });
  ['ego','hops','from','to'].forEach(i => document.getElementById(i).addEventListener('input', build));
  document.getElementById('reset').addEventListener('click', () => G.reset());

  document.getElementById('legend').innerHTML = Object.entries(G.STRENGTH_STYLE).map(([k, v]) =>
    `<span><i class="swatch" style="background:${v.colour}"></i>${k}</span>`).join('') +
    '<span>● person</span><span>■ organisation</span><span>◆ event</span>';

  build();
})().catch(e => document.getElementById('count').textContent = 'Could not load the map: ' + e.message);
""", '<script src="assets/js/graph.js"></script>')

# ---------------------------------------------------------------- timeline
page("timeline.html", "Timeline", "Chronology of the commission, colour-coded by workstream.", """
<h2 style="margin-top:0">Timeline</h2>
<p class="lead">Sitting days and off-stand events in one chronology. Colour marks the workstream.</p>
<div class="controls" id="ws-filter"></div>
<div class="controls">
  <label class="ctl"><input type="checkbox" id="show-days" checked> Sitting days</label>
  <label class="ctl"><input type="checkbox" id="show-events" checked> Events off the stand</label>
</div>
<div class="tl" id="tl"></div>
""", """
let META, DAYS, EVENTS, WS = new Set();

function render() {
  const sd = document.getElementById('show-days').checked;
  const se = document.getElementById('show-events').checked;
  let items = [];
  if (sd) items = items.concat(DAYS.filter(d => !WS.size || WS.has(d.workstream)).map(d => ({
    date: d.date, kind: 'day', ws: d.workstream,
    title: 'Day ' + d.day_number + ' — ' + (d.witnesses.length ? d.witnesses.map(w => w.name).join(', ') : 'documentary session'),
    body: d.summary, href: 'days.html?day=' + d.day_number + '#day-' + d.day_number, sources: d.sources })));
  if (se) items = items.concat(EVENTS.filter(e => e.date).map(e => ({
    date: e.date, kind: 'event', ws: null, title: e.title, body: e.description, sources: e.sources })));
  items.sort((a, b) => b.date.localeCompare(a.date));

  const colour = id => (META.workstreams.find(w => w.id === id) || {}).colour || 'var(--fg-3)';
  document.getElementById('tl').innerHTML = items.length ? items.map(i => `
    <div class="ev">
      <div class="d">${MT.esc(i.date)} ${i.kind === 'event' ? '· off the stand' : ''}</div>
      <div style="font-weight:600">${i.ws ? `<span class="ws-dot" style="background:${colour(i.ws)}"></span>` : ''}${
        i.href ? `<a href="${i.href}">${MT.esc(i.title)}</a>` : MT.esc(i.title)}</div>
      <p class="small" style="margin:4px 0">${MT.esc((i.body || '').slice(0, 260))}${(i.body || '').length > 260 ? '…' : ''}</p>
      <p class="small muted">${(i.sources || []).slice(0, 3).map(s =>
        `${MT.tierBadge(s.tier)} <a href="${MT.esc(s.url)}" target="_blank" rel="noopener noreferrer">${MT.esc(s.publisher || MT.host(s.url))}</a>`).join(' · ')}</p>
    </div>`).join('') : '<p class="empty">Nothing to show with those filters.</p>';
}

(async () => {
  [META, DAYS, EVENTS] = await MT.all('meta', 'days', 'events');
  document.getElementById('ws-filter').innerHTML = '<span class="small muted">Workstream:</span>' +
    META.workstreams.map(w => `<button class="chip" data-ws="${w.id}" aria-pressed="false"><span class="ws-dot" style="background:${w.colour}"></span>${MT.esc(w.label)}</button>`).join('');
  document.getElementById('ws-filter').addEventListener('click', ev => {
    const b = ev.target.closest('[data-ws]'); if (!b) return;
    const on = b.getAttribute('aria-pressed') === 'true';
    b.setAttribute('aria-pressed', String(!on));
    on ? WS.delete(b.dataset.ws) : WS.add(b.dataset.ws);
    render();
  });
  ['show-days','show-events'].forEach(i => document.getElementById(i).addEventListener('change', render));
  render();
})().catch(e => document.getElementById('tl').innerHTML = '<p class="empty">' + MT.esc(e.message) + '</p>');
""")

# ---------------------------------------------------------------- methodology
page("methodology.html", "Methodology", "The rules this tracker runs on, stated publicly, plus the gaps list.", """
<h2 style="margin-top:0">Methodology</h2>

<div class="card">
<h3 style="margin-top:0">1. This is a commission of inquiry, not a criminal trial</h3>
<p>Nobody appearing before the commission is an accused. The commission does not convict, acquit or
sentence. It hears evidence and it will make findings and recommendations. This site never uses the words
<em>accused</em>, <em>charges</em>, <em>verdict</em>, <em>guilty</em> or <em>defendant</em> about commission
proceedings. It uses: witness, implicated person, evidence leader, testimony, ruling, finding. Where a person
faces criminal proceedings in a separate matter before a court, that is stated as exactly that and cited.</p>
</div>

<div class="card">
<h3 style="margin-top:0">2. Every named person carries a status label</h3>
<div id="labels"></div>
</div>

<div class="card">
<h3 style="margin-top:0">3. Every factual claim carries a source tier</h3>
<p><span class="badge lbl-EVIDENCE">EVIDENCE</span> said under oath, or in an exhibit or affidavit before the commission.<br>
<span class="badge lbl-RULING">RULING</span> a ruling or direction by the chairperson.<br>
<span class="badge lbl-COURT">COURT</span> a judgment, cited to SAFLII.<br>
<span class="badge lbl-REPORTING">REPORTING</span> journalism not tested at the commission.</p>
<p><span class="badge lbl-PARTIAL">PARTIAL</span> marks a source where only a headline, title or lead could be read —
usually a paywall or a cookie wall. Nothing beyond what was actually read has been inferred from those.</p>
<p class="small muted">Reporting is never presented as evidence. Source-tier numbers on links —
<span class="badge tier-1">T1</span> the commission's own records, Parliament, SAFLII;
<span class="badge tier-2">T2</span> mainstream outlets; <span class="badge tier-3">T3</span> investigative outlets;
<span class="badge tier-4">T4</span> reference works, used only for biographical basics and photo licensing —
describe where a claim came from, not how strong it is.</p>
</div>

<div class="card">
<h3 style="margin-top:0">4. No fabrication</h3>
<p>Nothing on this site is invented. No date, day number, quote, exhibit reference or URL appears unless it
was actually retrieved from a source. Anything that could not be verified is omitted from the claim and
logged below rather than smoothed over. Where sources conflict, the conflict is stated instead of resolved by
preference.</p>
<p class="small muted" id="method-note"></p>
</div>

<div class="card">
<h3 style="margin-top:0">5. Quotation</h3>
<p>At most one quotation per source, under fifteen words, in quotation marks with attribution. Paraphrase is
preferred. Commission transcripts and rulings are public record and are the preferred source for any
quotation. The build script drops any quote that reaches the fifteen-word ceiling and logs it as a gap.</p>
</div>

<div class="card">
<h3 style="margin-top:0">6. Photographs</h3>
<p>The cascade is: freely-licensed or official commission images first, downloaded and credited; failing that a
press photo hotlinked with visible credit and a link to the source article; failing that an initials avatar.
No image of a real person is ever generated or synthesised. Every person record carries
<span class="mono">photo_source</span> and <span class="mono">photo_licence</span> fields.</p>
<p class="small muted" id="photo-note"></p>
</div>

<div class="card">
<h3 style="margin-top:0">7. Humour</h3>
<p>Light humour is used to keep the thing readable, and it is always visibly marked — italic, prefixed
<strong>😏 Aside:</strong> on the site and <span class="mono">[ASIDE]</span> in the email. A joke never sits
inside a factual sentence. Facts and jokes are separable on sight.</p>
<p class="aside-joke">Like this. Nothing load-bearing has ever been said in italics.</p>
</div>

<div class="card">
<h3 style="margin-top:0">8. Data layer</h3>
<p>The site renders entirely from JSON under <span class="mono">/data/</span>. No fact is hard-coded into
HTML. Weekly updates append to those files rather than rewriting them, and each week's briefing is archived
as <span class="mono">/briefings/YYYY-MM-DD.json</span>.</p>
<p class="small"><a href="data/days.json">days</a> · <a href="data/people.json">people</a> ·
<a href="data/orgs.json">orgs</a> · <a href="data/events.json">events</a> ·
<a href="data/edges.json">edges</a> · <a href="data/gaps.json">gaps</a> · <a href="data/meta.json">meta</a></p>
</div>

<h2>Gaps — what could not be verified</h2>
<p class="lead" id="gap-count"></p>
<div class="controls"><input type="search" id="gq" placeholder="Search the gaps list…" aria-label="Search gaps"></div>
<div id="gaps"></div>
""", """
let GAPS = [];
function renderGaps() {
  const q = document.getElementById('gq').value.trim().toLowerCase();
  const out = GAPS.filter(g => !q || (g.description + ' ' + g.would_resolve + ' ' + g.area).toLowerCase().includes(q));
  document.getElementById('gaps').innerHTML = out.length ? out.map(g => `
    <div class="card"><p style="margin:0 0 6px"><span class="badge tier-4">${MT.esc(g.area)}</span> ${MT.esc(g.description)}</p>
    <p class="small muted" style="margin:0"><strong>Would resolve it:</strong> ${MT.esc(g.would_resolve)}</p></div>`).join('')
    : '<p class="empty">No gap matches that search.</p>';
}
(async () => {
  const [meta, gaps, people] = await MT.all('meta', 'gaps', 'people');
  GAPS = gaps;
  document.getElementById('labels').innerHTML = meta.status_labels.map(s => {
    const n = people.filter(p => p.status === s).length;
    return `<p style="margin:6px 0">${MT.statusPill(s)} <span class="small muted">${n} ${n === 1 ? 'person' : 'people'}</span></p>`;
  }).join('') + '<p class="small muted">These six are the only labels used. There is no seventh.</p>';
  document.getElementById('method-note').textContent = meta.method_note || '';
  const noPhoto = people.filter(p => !p.photo_url).length;
  document.getElementById('photo-note').textContent =
    noPhoto + ' of ' + people.length + ' people currently render as initials avatars, because no freely-licensed ' +
    'photograph was located for them. That is logged as a gap, not hidden.';
  document.getElementById('gap-count').textContent =
    gaps.length + ' open gaps as at ' + meta.last_updated + '. Each says what would close it.';
  document.getElementById('gq').addEventListener('input', renderGaps);
  renderGaps();
})().catch(e => document.getElementById('gaps').innerHTML = '<p class="empty">' + MT.esc(e.message) + '</p>');
""")

print("\nPages written.")
