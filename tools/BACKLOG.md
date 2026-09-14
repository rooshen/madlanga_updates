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
