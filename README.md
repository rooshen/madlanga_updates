# The Madlanga Tracker

An independent tracker of the **Judicial Commission of Inquiry into Criminality, Political Interference and
Corruption in the Criminal Justice System** (the "Madlanga Commission"), chaired by retired Justice Mbuyiseli
Madlanga.

Static site, no build step, no runtime dependencies. Everything renders from JSON in `/data/`.

> **This is a commission of inquiry, not a criminal trial.** Nobody appearing before it is an accused, and
> nothing here is a verdict. See [Methodology](methodology.html) for the rules this project runs on.

---

## Status

**Phase 1 — scaffold.** The data layer holds the ten most recent sitting days (Days 155–164, 2026/08/06 to
2026/08/21) as a working sample. Days 1–154 are not back-filled yet. Every unverified item is logged in
`data/gaps.json` and surfaced publicly on the Methodology page.

## Layout

```
index.html          Home — this week's briefing
archive.html        Every past briefing, by date
days.html           Sitting days, filterable by date / witness / workstream
people.html         People cards with status labels
person.html?id=…    One person's profile plus their ego-network
map.html            Force-directed map of people, orgs, events and sourced edges
timeline.html       Chronology, colour-coded by workstream
methodology.html    The framing rules, stated publicly, plus the gaps list

data/meta.json      Workstreams, status labels, tier definitions, build stamp, counts
data/days.json      One record per sitting day
data/people.json    Name, role, status label, photo provenance, linked days
data/orgs.json      SAPS units, NPA, IDAC, IPID, parties, companies, municipalities
data/events.json    Meetings, appointments, disbandments, arrests, reports
data/edges.json     {from, to, type, strength, date, sources[]}
data/gaps.json      Everything unverified, with what would resolve it
briefings/          index.json + one YYYY-MM-DD.json per week

assets/css/app.css  Design tokens, dark default, light via toggle
assets/js/core.js   Data loader, chrome, badge/source/day renderers
assets/js/graph.js  Hand-rolled velocity-Verlet force simulation → SVG

tools/build_data.py Research payloads → the canonical /data layer
tools/make_pages.py Emits the HTML pages from a shared shell
tools/check.js      Headless-Chromium smoke test of every page
```

## Design decisions

**No framework, and no CDN either.** The force-directed graph is about 200 lines of hand-written
velocity-Verlet simulation rather than d3. That was not purism: the sandbox this was built in has no
outbound access to `cdnjs`, and a tracker that dies when a CDN has a bad day is a worse tracker. The site
loads three local files and nothing else — verified in `tools/check.js`, which fails the build if any page
requests an external origin.

**The map defaults to filtered.** `alleged` edges are hidden on first load. An unfiltered hairball of 57
relationships communicates nothing, and showing untested allegations at the same visual weight as sworn
testimony would break the framing rules on sight. Edge colour and dash pattern encode strength; every edge
opens its own citation list on click.

**Nothing is hard-coded into HTML.** Weekly updates append to `/data/` and the pages re-render. If a fact
appears on this site and is not in a JSON file, that is a bug.

**Quote ceiling is enforced in code.** `build_data.py` drops any quotation of fifteen words or more and logs
it as a gap rather than shipping it.

## Rebuilding

```bash
python3 tools/build_data.py     # research payloads → data/*.json
python3 tools/make_pages.py     # → *.html
python3 -m http.server 8899     # serve locally
node tools/check.js             # headless smoke test: console errors, 404s, external requests, mobile overflow
```

`build_data.py` reads `days_raw.json` and `people_raw.json` from the parent directory. Those are research
payloads, deliberately kept out of the repo — the repo holds the validated output, not the working notes.

## Deploying to GitHub Pages

The site is plain static files at the repo root, so Pages needs no workflow and no build.

1. Create a repository named `madlanga_updates`.
2. Push this directory to it on `main`.
3. Repo **Settings → Pages** → Source: **Deploy from a branch** → Branch: `main`, folder: `/ (root)` → Save.
4. Wait one to two minutes. The site appears at `https://<username>.github.io/madlanga_updates/`.

`.nojekyll` is present so GitHub serves the files as-is rather than running them through Jekyll.

## Licence and use

Commission transcripts, rulings and exhibits are public record. Journalism cited here belongs to its
publishers and is linked, quoted under fifteen words, and credited — never reproduced. Photographs are used
only under a reusable licence, or hotlinked with visible credit, or replaced with an initials avatar. No
image of a real person is ever generated.
