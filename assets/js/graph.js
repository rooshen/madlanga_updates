/* Force-directed graph — hand-rolled velocity-Verlet simulation, SVG output.
   No d3, no CDN, no build step. ~90 nodes is well inside O(n^2) budget. */

function ForceGraph(svg, opts = {}) {
  const NS = 'http://www.w3.org/2000/svg';
  const el = (n, a = {}) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); return e; };

  const root  = el('g');
  const gLink = el('g', { class: 'links' });
  const gNode = el('g', { class: 'nodes' });
  root.appendChild(gLink); root.appendChild(gNode); svg.appendChild(root);

  let nodes = [], links = [], view = { x: 0, y: 0, k: 1 }, alpha = 0, raf = null, dragNode = null;
  const STRENGTH_STYLE = {
    testified:  { colour: '#4ea672', dash: null,    width: 2.2, label: 'testified' },
    documented: { colour: '#5b9bd5', dash: null,    width: 2.0, label: 'documented' },
    alleged:    { colour: '#c9a227', dash: '5 4',   width: 1.5, label: 'alleged' },
    denied:     { colour: '#e2725b', dash: '2 4',   width: 1.5, label: 'denied' },
  };

  function size() { const r = svg.getBoundingClientRect(); return { w: r.width || 800, h: r.height || 500 }; }

  function apply() { root.setAttribute('transform', `translate(${view.x} ${view.y}) scale(${view.k})`); }

  /* ---------------- simulation ---------------- */
  function tick() {
    const { w, h } = size(), cx = w / 2, cy = h / 2;
    const n = nodes.length;
    if (!n) return;

    // many-body repulsion
    for (let i = 0; i < n; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < n; j++) {
        const b = nodes[j];
        let dx = b.x - a.x, dy = b.y - a.y;
        let d2 = dx * dx + dy * dy;
        if (d2 < 1) { dx = (Math.random() - 0.5) * 2; dy = (Math.random() - 0.5) * 2; d2 = dx * dx + dy * dy + 1; }
        const d = Math.sqrt(d2);
        const f = (opts.charge ?? -2400) / d2;
        const fx = (dx / d) * f, fy = (dy / d) * f;
        a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;

        // collision — radius includes the label box so captions stop colliding
        const minD = a.pad + b.pad;
        if (d < minD) {
          const push = (minD - d) / d * 0.5;
          a.vx -= dx * push; a.vy -= dy * push; b.vx += dx * push; b.vy += dy * push;
        }
      }
    }

    // link springs
    for (const l of links) {
      const a = l.s, b = l.t;
      const dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.sqrt(dx * dx + dy * dy) || 1;
      const rest = l.rest;
      const f = (d - rest) * 0.035 * l.k;
      const fx = (dx / d) * f, fy = (dy / d) * f;
      const ma = 1 / (1 + a.deg), mb = 1 / (1 + b.deg);
      a.vx += fx * ma * 2; a.vy += fy * ma * 2;
      b.vx -= fx * mb * 2; b.vy -= fy * mb * 2;
    }

    // centring + integrate. Elliptical pull keeps it wide rather than round,
    // which suits a landscape viewport and stops the label pile-up in the middle.
    for (const p of nodes) {
      if (p === dragNode) { p.vx = p.vy = 0; continue; }
      p.vx += (cx - p.x) * 0.006;
      p.vy += (cy - p.y) * 0.016;
      p.vx *= 0.84; p.vy *= 0.84;
      p.x += p.vx * alpha; p.y += p.vy * alpha;
      const m = 26;
      p.x = Math.max(m, Math.min(w - m, p.x));
      p.y = Math.max(m, Math.min(h - m, p.y));
    }
    draw();
  }

  function draw() {
    for (const l of links) {
      l.el.setAttribute('x1', l.s.x); l.el.setAttribute('y1', l.s.y);
      l.el.setAttribute('x2', l.t.x); l.el.setAttribute('y2', l.t.y);
    }
    for (const p of nodes) p.el.setAttribute('transform', `translate(${p.x} ${p.y})`);
  }

  function run(a = 1) {
    alpha = a;
    if (raf) cancelAnimationFrame(raf);
    const step = () => {
      tick();
      alpha *= 0.982;
      if (alpha > 0.02) raf = requestAnimationFrame(step); else raf = null;
    };
    raf = requestAnimationFrame(step);
  }

  /* ---------------- build ---------------- */
  function set(nodeData, linkData) {
    gLink.textContent = ''; gNode.textContent = '';
    const { w, h } = size();
    const byId = {};
    const deg = {};
    linkData.forEach(l => { deg[l.from] = (deg[l.from] || 0) + 1; deg[l.to] = (deg[l.to] || 0) + 1; });

    nodes = nodeData.map((d, i) => {
      const ang = (i / nodeData.length) * Math.PI * 2;
      const dg = deg[d.id] || 0;
      const r = d.kind === 'org' ? 8 : d.kind === 'event' ? 6 : 6 + Math.min(7, dg * 0.9);
      const short = d.label.length > 22 ? d.label.slice(0, 21) + '…' : d.label;
      const p = { ...d, deg: dg, r, short,
        pad: Math.max(r + 8, short.length * 2.6),      // half the label box, for collision
        x: w / 2 + Math.cos(ang) * w * 0.40,
        y: h / 2 + Math.sin(ang) * h * 0.40, vx: 0, vy: 0 };
      byId[d.id] = p;
      return p;
    });

    links = linkData.filter(l => byId[l.from] && byId[l.to]).map(l => {
      const st = STRENGTH_STYLE[l.strength] || STRENGTH_STYLE.alleged;
      const s = byId[l.from], t = byId[l.to];
      const line = el('line', { class: 'link', stroke: st.colour, 'stroke-width': st.width, 'stroke-opacity': 0.72 });
      if (st.dash) line.setAttribute('stroke-dasharray', st.dash);
      line.style.cursor = 'pointer';
      line.addEventListener('click', ev => { ev.stopPropagation(); opts.onLink && opts.onLink(l, s, t); });
      gLink.appendChild(line);
      return { ...l, s, t, el: line, k: st.width / 2,
               rest: Math.max(110, s.pad + t.pad + 30) };
    });

    for (const p of nodes) {
      const g = el('g', { class: 'nodeg' });
      if (p.kind === 'org') {
        g.appendChild(el('rect', { x: -p.r, y: -p.r, width: p.r * 2, height: p.r * 2, rx: 2,
          fill: p.colour, stroke: 'var(--bg-2)', 'stroke-width': 1.5 }));
      } else if (p.kind === 'event') {
        g.appendChild(el('polygon', { points: `0,${-p.r - 1} ${p.r + 1},0 0,${p.r + 1} ${-p.r - 1},0`,
          fill: p.colour, stroke: 'var(--bg-2)', 'stroke-width': 1.5 }));
      } else {
        g.appendChild(el('circle', { r: p.r, fill: p.colour, stroke: 'var(--bg-2)', 'stroke-width': 1.5 }));
      }
      const txt = el('text', { x: 0, y: p.r + 12, 'text-anchor': 'middle',
        stroke: 'var(--bg-2)', 'stroke-width': '3', 'paint-order': 'stroke' });
      txt.textContent = p.short;
      g.appendChild(txt);
      const full = el('title'); full.textContent = p.label; g.appendChild(full);
      g.addEventListener('click', ev => { ev.stopPropagation(); opts.onNode && opts.onNode(p); });
      g.addEventListener('pointerdown', ev => {
        ev.stopPropagation(); dragNode = p; g.setPointerCapture(ev.pointerId);
      });
      g.addEventListener('pointermove', ev => {
        if (dragNode !== p) return;
        const r = svg.getBoundingClientRect();
        p.x = (ev.clientX - r.left - view.x) / view.k;
        p.y = (ev.clientY - r.top - view.y) / view.k;
        if (!raf) draw();
        run(Math.max(alpha, 0.35));
      });
      const end = () => { dragNode = null; };
      g.addEventListener('pointerup', end); g.addEventListener('pointercancel', end);
      gNode.appendChild(g);
      p.el = g;
    }
    run(1);
    return { nodes: nodes.length, links: links.length };
  }

  /* ---------------- pan / zoom ---------------- */
  let panning = null;
  svg.addEventListener('pointerdown', ev => {
    if (dragNode) return;
    panning = { x: ev.clientX, y: ev.clientY, vx: view.x, vy: view.y };
    svg.classList.add('dragging'); svg.setPointerCapture(ev.pointerId);
  });
  svg.addEventListener('pointermove', ev => {
    if (!panning) return;
    view.x = panning.vx + (ev.clientX - panning.x);
    view.y = panning.vy + (ev.clientY - panning.y);
    apply();
  });
  const stopPan = () => { panning = null; svg.classList.remove('dragging'); };
  svg.addEventListener('pointerup', stopPan);
  svg.addEventListener('pointercancel', stopPan);
  svg.addEventListener('wheel', ev => {
    ev.preventDefault();
    const r = svg.getBoundingClientRect();
    const mx = ev.clientX - r.left, my = ev.clientY - r.top;
    const k2 = Math.max(0.25, Math.min(3.5, view.k * (ev.deltaY < 0 ? 1.12 : 1 / 1.12)));
    view.x = mx - (mx - view.x) * (k2 / view.k);
    view.y = my - (my - view.y) * (k2 / view.k);
    view.k = k2; apply();
  }, { passive: false });

  function reset() { view = { x: 0, y: 0, k: 1 }; apply(); run(1); }

  return { set, run, reset, STRENGTH_STYLE };
}
