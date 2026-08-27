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

## Status as of 2026/08/26 ~21:25 UTC
- Extracted + merged + shipped: Days 1-15 (pilot), 17-30, 31-34 (partial synthesis), 35-42.
- Downloaded as PDF to the user's Mac (`~/Downloads/mad-day-0NN.pdf`) but NOT yet staged/
  converted/extracted: Days 92-166 minus the gap days above (69 files) — staging blocked this
  run by `untrusted_device` (user needs to re-auth the desktop app; do not retry blindly).
- Downloaded and converted to .txt, NOT yet extracted: Days 43-50, 51-90 range (minus 56/85/90).
- Never downloaded: Day 14 (re-fetch), Day 16 confirmed genuinely missing.

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
