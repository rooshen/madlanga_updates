# Phase 2 back-fill — working notes (not published, repo-internal)

## Scale discovered 2026/08/26
The commission has sat far more than the ~90 days assumed earlier. As of 2026/08/26 the
hearings index (see below) runs to **Day 166** (25 Aug 2026), spanning 2025/09/17 to date.

## Day → date index (source of truth)
Fetch fresh each run — do not hardcode, the index grows daily:

```
GET https://kygcssfahsvxmdvynbge.supabase.co/rest/v1/hearings?select=*&order=hearing_date.desc
Header: apikey: sb_publishable_SyZh-y7K_XNAObUzSdLfxg_iAeGEyVq
```
This is the commission's own public anon/publishable key, already embedded client-side in
their site bundle (`/assets/index-*.js`, search for `sb_publishable_`) — not a secret, safe to
call directly (works from a plain `fetch`/`curl`, no Chrome automation needed for this step).
Each row has `day_number`, `hearing_date` (YYYY-MM-DD), `id` (hearing uuid).

To get a specific day's materials:
```
GET https://kygcssfahsvxmdvynbge.supabase.co/rest/v1/hearing_media?select=*&hearing_id=eq.<id>
```
Filter `kind === 'transcript'` — this is deterministic and far more reliable than the old
filename-regex heuristic (kept only as a fallback for older days where `kind` may be absent).
The transcript row's `file_path` feeds the signed-URL download:
```
POST https://kygcssfahsvxmdvynbge.supabase.co/storage/v1/object/sign/hearing-media/<file_path>
Headers: apikey: <same key>, Content-Type: application/json
Body: {"expiresIn": 120}
```
Response `.signedURL` is a path; prefix with `https://kygcssfahsvxmdvynbge.supabase.co/storage/v1`
and fetch it directly for the PDF bytes (works via plain JS `fetch`, tested from a Chrome tab —
untested from the cloud sandbox's own network, which is normally egress-restricted to this
domain; Chrome automation remains the fallback if direct fetch is ever blocked).

## Known transcript gaps (as of 2026/08/26 — re-check `hearing_media` each run, this list can change)
Day 16, 56, 85, 90, 91, 104, 124, 125, 130, 131, 143 — no `kind:'transcript'` media row.
Day 14 also needs re-fetching in the container (a stale/bad local file was deleted earlier this
project and never replaced).
Day 161 (18 Aug 2026) has a transcript despite the sitting itself being reported as the
scheduled witness (Vusimuzi Matlala) being postponed — it exists, download and process as normal.

## PHASE 2 BACK-FILL COMPLETE — 2026/09/05 ~05:20 UTC
Every commission sitting day from Day 1 to Day 166 has now been extracted, quote-verified, merged,
built and delivered to the user's Mac, except:
- **Day 14**: unresolved. `mad-day-014.pdf` on the user's Mac is actually a witness-statement
  exhibit ("Statement of ICB"), not the Day 14 hearing transcript. Its real transcript, if the
  commission's index still lists one, has not been located.
- **11 confirmed gap days** (16, 56, 85, 90, 91, 104, 124, 125, 130, 131, 143): the commission
  itself published no transcript media for these — nothing to back-fill.

`meta.json`'s `days_outstanding` is now 1 (Day 14 only) and `confirmed_gap_days` lists the 11
genuine gaps. The stale Methodology page `method_note` (a leftover description of an early
Tier-2/3-only phase) was rewritten to describe this completed state.

**Ongoing work from here is forward-looking, not backfill**: as the commission continues sitting,
new days should be added following the same pipeline (see CLAUDE.md's "The pipeline, batch by
batch" section) as their transcripts become available via the Supabase hearings index or the
user's own downloads. Days 155-156 had in fact already been extracted and merged in an earlier
run before this session reached them again on 2026/09/05 — `merge_backfill.py`'s day-number dedup
correctly skipped re-adding them rather than overwriting good data, which is why a "Days 151-157"
merge reported only "+4 added" for days. Always trust that dedup over assuming something is
missing just because a re-run's batch summary doesn't add every day you expected.

## Forward-looking batch — Days 167-178 (added 2026/09/27)
Processed the commission's next 12 sitting days (167-178) via the standard pipeline. Quote
verification: 63 kept / 14 dropped, 81.8% pass rate — in line with historical batches. Counts:
154 → 166 days, 259 → 275 people (net of one merge), 106 → 104 orgs (net of one merge), 209 → 211
edges.

Key content: General Godfrey Lebeya finally testified in person (Days 168, 171-172), moving his
own status from "Implicated (untested)" to "Testified"; Lt Col Deena Govender continued his
Mchunu/Ntandani pressure-campaign testimony (Day 170); a JMPD-linked case network came out via
Superintendent De Beer and Sgt Van Wyk (Day 173, naming Manyama, Mphahlele, Pakwani, Rikhotso,
Matimu, Mokgatle, Mgujulwa, and an unidentified officer known only as "Mosquito"); DCS witness
Thobakgale and PSC witness/analyst Fikeni testified (Days 174/176); Sibanyoni's further
cross-examination was postponed (Day 177) after a scheduling conflict.

**Sandbox-reset lesson**: the sandbox holding `/home/claude/days_raw.json` and
`/home/claude/people_raw.json` (the gitignored raw research payloads `build_data.py` reads) had
been reclaimed between sessions, destroying both files — they are session-local working state,
never delivered to the user's Mac and not in git. Reconstructed both losslessly from the
last-built `data/*.json` (`reconstruct_raw.py`, verified via a zero-diff round-trip against a
pre-reconstruction snapshot) before this batch could proceed. **Worth considering for a future
session**: back these up somewhere durable (e.g. deliver a copy to the Mac periodically, or
commit a redacted/structural copy) so a sandbox reset doesn't force a reconstruction detour again.

**Data-quality fixes made while processing this batch** (found via the now-routine
duplicate-detection check run before merging any batch — worth keeping as standard practice):
- Merged a pre-existing duplicate person record, `general-lebeya` into `general-godfrey-lebeya`
  (same person; missed by the 2026/09/13 dedup pass, which only ran on more clearly-matching name
  variants).
- Merged a pre-existing duplicate org record, `johannesburg-metro-police-department-jmpd` into
  `johannesburg-metropolitan-police-department-jmpd` (same organisation; the 2026/09/13 dedup
  pass only covered `people`, never `orgs` — this is the first org-level dedup fix on record. A
  future session should consider running a proper org-dedup pass, similar to `dedup_people.py`,
  rather than relying on catching these one at a time).
- Normalized two witness-name variants *within this batch itself* before merging, so they
  slug-matched existing/sibling records instead of spawning new duplicates: Lt Col Govender's
  name (Day 170, "Colonel (Lt-Col/Lt-Gen) Govender" → the canonical full name already used by his
  existing record) and Sibanyoni's name (Day 177 used reversed word order vs Day 169 within the
  same batch).
- Trimmed over-inclusive `witnesses[]` arrays on Days 171 and 173, which had listed named-but-
  non-testifying implicated individuals alongside the day's actual witness — left as-is, these
  would have been auto-stubbed as "Testified" by `build_data.py`'s witness-to-person mechanism.
  The non-testifying individuals were instead added as ordinary `people` entries with their
  correctly-extracted status (Implicated untested / not yet responded / criminally charged, as
  appropriate).

**Flagged but explicitly NOT merged**: `deena-govender` vs
`lieutenant-colonel-deenadayalan-deena-govender` remain two separate person records. Both
describe testimony/allegations involving a "Govender" in KZN policing, but reference different
specific named victims — merging without re-reading the source transcripts risks misattributing
one real person's alleged conduct to another. Left for a future session with time to verify
against the transcripts directly.

Replaced reliance on `tools/merge_backfill.py` for this batch with a purpose-built script
(`/home/claude/custom_merge_167_178.py`) — `merge_backfill.py`'s expected raw-payload schema
(`venue`, `evidence_leaders`, `sworn`, `protected_identity`, etc.) does not match what
`build_data.py` actually reads back out of `days_raw.json`, and it hardcodes every witness's
`status_hint` to `"testified"` regardless of their actual role in that day's proceedings — which
would have mis-classified several implicated-but-not-testifying people as literal witnesses if
used as-is on this batch. `merge_backfill.py` itself was left unmodified; a future session doing
another batch should check whether it's worth fixing properly rather than writing another
one-off script.

## Improvement pass — 2026/09/13
On top of the completed backfill: deduped 38 person name-variant groups (see `dedup_people.py` in
`/home/claude`, edits the raw payloads not the build output — 324 → 259 built people); replaced the
unbound daily automation trigger with a bound one; added site-wide search (`search.html`), a
"What's new" changelog (`changelog.html` / `data/changelog.json`, hand-maintained), an Entities-page
rand-figure rollup stat, and a gap-day help note on `days.html` (Day 14 + the 11 confirmed gaps,
linking to a GitHub issue). Rewrote the stale "Phase 2 back-fill in progress" wording in
`meta.json`'s `phase` field and the home page banner to reflect the completed backfill. Confirmed
the user has already pushed everything to GitHub themselves — see CLAUDE.md's "Where things stand"
for the git-history-divergence note.

## Prior status log (for history — see git log for full detail)
- `device_stage_files` was unblocked on 2026/09/04 after the user re-authenticated the desktop app.
- A mid-batch rate limit hit on 2026/09/04 ~22:37 UTC during Days 132-140 (reset stated as
  02:10 UTC); 5 of 9 agent calls actually completed successfully despite all 9 reporting
  "terminated early" errors — always re-check `/home/claude/day_json/` for what actually landed
  before re-firing a "failed" batch, rather than trusting the error message alone.
- **Day 14 is NOT the DPCI Port Shepstone/Aeroton transcript** — attempted staging and pdftotext
  conversion on 2026/09/04 revealed `mad-day-014.pdf` on the user's Mac is actually a 63-page
  in-camera witness statement exhibit ("Statement of ICB", covering Matlala/Nkosi/Shibiri/Matjeng/
  Gundowan), NOT a sitting-day hearing transcript. Do not extract it as Day 14 — that would put
  wrong content under the wrong day number. Day 14's real transcript, if the commission's hearing
  index still lists one, has not been located. Treat Day 14 as unresolved, not merely blocked.
- Day 16, 56, 85, 90, 91, 104, 124, 125, 130, 131, 143 confirmed genuinely missing (no transcript
  media exists for these).

## Site feature: Entities tab (added 2026/09/04)
`entities.html` (generated by `tools/make_pages.py`, added to nav in `assets/js/core.js`, smoke-
tested in `tools/check.js`) lists every org in `data/orgs.json` with its description, people
linked via `data/edges.json`, and rand figures extracted client-side from those descriptions/edge
types via regex — clearly labelled as figures already stated in the record, not a new calculation
or verified total. No backend/data-schema change was needed; it's derived entirely from existing
JSON. If a future batch's synthesis adds richer org descriptions (what happened to the entity,
outcome, value), this page picks them up automatically — no page-level work needed per batch.

## Reusable extraction workflow
`tools/wf_extract_batch.js` (Workflow script, run via the Workflow tool with
`scriptPath: 'tools/wf_extract_batch.js'`, `args: {days: [...]}` — each item needs
`day_number`, `transcript_path`, and optionally `date_hint`/`weekday_hint`/`witness_hint`/
`el_hint`). Batch size 8-10 days has run reliably; larger batches have hit session token
limits mid-run. After a batch completes: normalize `date` and `reporting_context[].retrieved`
from `YYYY-MM-DD` to `YYYY/MM/DD`, run `tools/verify_quotes.py`, extract the `synthesis` key to
its own file (never pass the whole `{days, synthesis}` wrapper to `--synthesis` — it silently
merges nothing), run `tools/merge_backfill.py`, `tools/build_data.py`, `tools/make_pages.py`,
`node tools/check.js`, commit locally, then deliver via SendUserFile + device_commit_files
(force:true) — never run `git` via `device_bash`, not even read-only status checks.
