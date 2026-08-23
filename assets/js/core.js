/* The Madlanga Tracker — shared runtime. No dependencies, no build step. */

const MT = (() => {
  // Works at a domain root and under a GitHub Pages project path (/madlanga_updates/).
  const parts = location.pathname.split('/');
  parts.pop();
  const BASE = parts.join('/') + '/';

  const cache = {};
  async function data(name) {
    if (!cache[name]) {
      cache[name] = fetch(BASE + 'data/' + name + '.json', { cache: 'no-cache' })
        .then(r => { if (!r.ok) throw new Error(name + ': HTTP ' + r.status); return r.json(); });
    }
    return cache[name];
  }
  async function all(...names) { return Promise.all(names.map(data)); }

  async function briefing(file) {
    const r = await fetch(BASE + 'briefings/' + file, { cache: 'no-cache' });
    if (!r.ok) throw new Error('briefing ' + file + ': HTTP ' + r.status);
    return r.json();
  }

  /* ---------- escaping ---------- */
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  /* ---------- chrome ---------- */
  const NAV = [
    ['index.html', 'Home'], ['archive.html', 'Archive'], ['days.html', 'Hearing days'],
    ['people.html', 'People'], ['map.html', 'The Map'], ['timeline.html', 'Timeline'],
    ['methodology.html', 'Methodology'],
  ];

  function theme(init) {
    const root = document.documentElement;
    if (init) {
      let t = null;
      try { t = localStorage.getItem('mt-theme'); } catch (e) { /* private mode */ }
      if (t === 'light' || t === 'dark') root.setAttribute('data-theme', t);
      return;
    }
    const next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('mt-theme', next); } catch (e) { /* ignore */ }
  }
  theme(true);

  function chrome(page) {
    const here = location.pathname.split('/').pop() || 'index.html';
    document.body.insertAdjacentHTML('afterbegin', `
<header class="site"><div class="wrap">
  <div class="brand">
    <h1><a href="${BASE}index.html">The Madlanga Tracker</a></h1>
    <span class="sub">Judicial Commission of Inquiry &middot; independent tracker</span>
  </div>
  <nav class="site">
    ${NAV.map(([h, l]) => `<a href="${BASE}${h}"${h === here ? ' aria-current="page"' : ''}>${l}</a>`).join('')}
    <button class="theme-btn" id="theme-btn" type="button" aria-label="Toggle light and dark mode">◐ Theme</button>
  </nav>
</div></header>`);
    document.getElementById('theme-btn').addEventListener('click', () => theme(false));

    document.body.insertAdjacentHTML('beforeend', `
<footer class="site"><div class="wrap">
  <p>An independent tracker of the Judicial Commission of Inquiry into Criminality, Political Interference
  and Corruption in the Criminal Justice System. Not affiliated with the commission, the Presidency or any
  party before it. This is a <strong>commission of inquiry, not a criminal trial</strong> &mdash; nobody here
  is an accused and nothing here is a verdict.</p>
  <p>Dates YYYY/MM/DD &middot; times SAST (HH24:MI) &middot; South African English.
  <a href="${BASE}methodology.html">Methodology and gaps</a> &middot;
  <span id="foot-stamp" class="mono"></span></p>
</div></footer>`);
    data('meta').then(m => {
      const el = document.getElementById('foot-stamp');
      if (el) el.textContent = 'Data last built ' + m.last_updated;
    }).catch(() => {});
  }

  /* ---------- formatting helpers ---------- */
  const tierBadge = t => t ? `<span class="badge tier-${t}" title="Source tier ${t}">T${t}</span>` : '';

  function claimBadge(label) {
    return `<span class="badge lbl-${esc(label)}">${esc(label)}</span>`;
  }

  function statusPill(s) {
    return `<span class="status" data-s="${esc(s)}">${esc(s)}</span>`;
  }

  function wsDot(id, meta) {
    const w = (meta.workstreams || []).find(x => x.id === id);
    if (!w) return '';
    return `<span class="ws-dot" style="background:${w.colour}"></span><span class="small muted">${esc(w.label)}</span>`;
  }

  function host(u) { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return u; } }

  function sourceList(sources) {
    if (!sources || !sources.length) return '<p class="small muted">No source recorded. Logged as a gap.</p>';
    return '<ul class="srcs">' + sources.map(s => `<li>${tierBadge(s.tier)}${
      s.partial ? '<span class="badge lbl-PARTIAL" title="Only a headline, title or lead could be read">PARTIAL</span>' : ''
    }<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.publisher || host(s.url))}</a>${
      s.retrieved ? `<span class="muted small">retrieved ${esc(s.retrieved)}</span>` : ''
    }</li>`).join('') + '</ul>';
  }

  function avatar(p) {
    if (p.photo_url) {
      return `<img class="avatar" src="${esc(p.photo_url)}" alt="${esc(p.name)}" loading="lazy"
        onerror="this.outerHTML='<div class=&quot;avatar&quot;>${esc(p.initials)}</div>'">`;
    }
    return `<div class="avatar" aria-hidden="true">${esc(p.initials)}</div>`;
  }

  /* dd of quotes, capped at the 15-word house rule */
  function quoteBlock(q) {
    return `<blockquote class="q">&ldquo;${esc(q.text)}&rdquo;
      <cite>${esc(q.speaker || 'Speaker not recorded')} &middot; ${claimBadge(q.tier_label || 'REPORTING')}
      ${q.source_url ? `&middot; <a href="${esc(q.source_url)}" target="_blank" rel="noopener noreferrer">source</a>` : ''}</cite>
    </blockquote>`;
  }

  function dayCard(d, meta, opts = {}) {
    const ws = (meta.workstreams || []).find(x => x.id === d.workstream);
    const wit = d.witnesses.length
      ? d.witnesses.map(w => `<a href="${BASE}person.html?id=${encodeURIComponent(w.person_id)}">${esc(w.name)}</a>`).join(', ')
      : '<span class="muted">No oral evidence &mdash; documentary session</span>';
    return `
<article class="card day" style="border-left-color:${ws ? ws.colour : 'var(--line)'}" id="day-${d.day_number}">
  <div class="head">
    <span class="num">Day ${d.day_number ?? '?'}</span>
    ${d.day_number_verified ? '' : '<span class="badge lbl-PARTIAL" title="Day number inferred from adjacent verified days, not read from a single source">DAY № INFERRED</span>'}
    <span class="date">${esc(d.date)} &middot; ${esc(d.weekday || '')}</span>
    ${ws ? `<span class="small">${wsDot(d.workstream, meta)}</span>` : ''}
  </div>
  <p class="who"><strong>Witness:</strong> ${wit}${
    d.evidence_leaders && d.evidence_leaders.length
      ? ` &nbsp;·&nbsp; <strong>Evidence ${d.evidence_leaders.length > 1 ? 'leaders' : 'leader'}:</strong> ${esc(d.evidence_leaders.join(' & '))} <span class="badge tier-1" title="From the commission's own hearings index">T1</span>`
      : ''}</p>
  ${d.tier1 && d.tier1.listed ? `<p class="small muted">Commission record for this day:
     <a href="${esc(d.tier1.url)}" target="_blank" rel="noopener noreferrer">official page</a> —
     ${esc(d.tier1.witness_line)} Full transcript and audio are downloadable there and have
     <strong>not</strong> yet been read into this summary.</p>` : ''}
  ${(d.conflicts || []).map(c => `<div class="notice"><strong>Tier 1 / Tier 2 conflict.</strong>
     <span class="badge tier-1">T1</span> ${esc(c.tier1)}
     <span class="badge tier-2">T2/T3</span> ${esc(c.other)}
     <em>${esc(c.resolution)}</em></div>`).join('')}
  <p class="sum">${esc(d.summary)}</p>
  ${d.rulings.length ? `<div>${d.rulings.map(r => `<p class="small">${claimBadge('RULING')} ${esc(r.description)}
      ${r.source_url ? `<a href="${esc(r.source_url)}" target="_blank" rel="noopener noreferrer">source</a>` : ''}</p>`).join('')}</div>` : ''}
  ${d.quotes.length ? d.quotes.map(quoteBlock).join('') : ''}
  ${d.exhibits.length ? `<details><summary>Exhibits referenced (${d.exhibits.length})</summary>
      <ul class="tight small">${d.exhibits.map(e => `<li>${e.ref ? `<strong class="mono">${esc(e.ref)}</strong> &mdash; ` : ''}${esc(e.description)}</li>`).join('')}</ul></details>` : ''}
  ${d.unverified.length ? `<details><summary>Loose ends &amp; what is not verified (${d.unverified.length})</summary>
      <ul class="tight small muted">${d.unverified.map(u => `<li>${esc(u)}</li>`).join('')}</ul></details>` : ''}
  <details${opts.openSources ? ' open' : ''}><summary>Sources (${d.sources.length})${d.video_url ? ' &amp; video' : ''}</summary>
    ${d.video_url ? `<p class="small">▶ <a href="${esc(d.video_url)}" target="_blank" rel="noopener noreferrer">Broadcast recording for this sitting day</a></p>` : ''}
    ${sourceList(d.sources)}
  </details>
</article>`;
  }

  return { BASE, data, all, briefing, esc, chrome, tierBadge, claimBadge, statusPill, wsDot,
           sourceList, avatar, quoteBlock, dayCard, host };
})();
