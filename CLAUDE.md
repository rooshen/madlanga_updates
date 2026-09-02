# CLAUDE.md — orientation for a fresh Claude session on this repo

You are picking up **The Madlanga Tracker**: an independent static-site tracker of South Africa's
Judicial Commission of Inquiry into Criminality, Political Interference and Corruption in the
Criminal Justice System (the "Madlanga Commission"), chaired by retired Justice Mbuyiseli Madlanga.
Repo: `rooshen/madlanga_updates`. Deployed (once pushed) at `https://rooshen.github.io/madlanga_updates/`.

Read `README.md` first — it documents the site architecture, file layout and design decisions and is
kept accurate. This file covers what README doesn't: the standing task, the framing rules, the
extraction pipeline, known infrastructure problems, and exactly where things stand.

## The standing instruction

The user's governing instruction for this whole project: **process the commission's sitting-day
transcripts into the tracker, one manageable batch at a time, with real research on other news
sources for corroboration, and whenever nearing a token/session limit, stop and ship whatever is
done rather than losing it.** There is no separate "done" signal to wait for — the commission is
still sitting, so this is a running backlog. Treat any fresh session on this repo as a continuation
of that instruction unless the user says otherwise: check `tools/BACKLOG.md` for the current state,
pick up the next unprocessed batch, and keep going.

## Hard framing rules (non-negotiable, drive every extraction)

- **This is a commission of inquiry, not a criminal trial.** Never use: accused, charges, verdict,
  guilty, defendant. Always: witness, implicated person, evidence leader, testimony, ruling, finding.
- Every named person must map to exactly one status from a **closed list**: Testified / Implicated
  (denied) / Implicated (not yet responded) / Implicated (untested) / Criminally charged in a
  separate matter / Commission official. See `data/meta.json` for the canonical list and
  `methodology.html` for the public explanation.
- **4-tier source system**: Tier 1 = the transcript itself (EVIDENCE — what a witness actually said
  under oath, or a commission RULING). Tier 2 = mainstream reporting (SABC News, News24, TimesLIVE,
  EWN, IOL). Tier 3 = investigative journalism (Daily Maverick, amaBhungane, Mail & Guardian,
  GroundUp). Tier 2/3 material goes ONLY in a day record's `reporting_context` array — never
  merged into the Tier-1 summary/quotes — and must read as *reported*, not asserted as fact.
  Don't use outlets outside this whitelist.
- **Quotes**: under 15 words, exact substring of the source (transcript or article), with a speaker.
  Never invent or paraphrase-as-quote. `tools/verify_quotes.py` mechanically checks every quote as a
  normalized substring match and drops anything that fails — this is the anti-fabrication backstop,
  trust the script over your own recollection of what you wrote.
- **No fabrication generally**: if it's not in the transcript, don't guess — put it in `unverified`
  or leave it out.

## The pipeline, batch by batch

1. **Get the transcript.** Day → date index and transcript download: `GET
   https://kygcssfahsvxmdvynbge.supabase.co/rest/v1/hearings?select=*&order=hearing_date.desc` with
   header `apikey: sb_publishable_SyZh-y7K_XNAObUzSdLfxg_iAeGEyVq` (the commission's own public key,
   safe to call directly — no browser automation needed). Then `hearing_media?select=*&hearing_id=eq.<id>`
   filtered to `kind === 'transcript'`, sign the `file_path` via the storage `/sign/` endpoint, fetch
   the PDF. Full detail in `tools/BACKLOG.md`.
2. **Extract each day to JSON** using the schema and rules embedded in `/home/claude/gen_prompt.py`
   (`extract_prompt()`) — regenerate `/tmp/prompt_N.txt` files with it if they're missing (they don't
   survive container restarts). See "Workflow tool is broken" below for how extraction is actually run.
   Output: one `/home/claude/day_json/day_0NN.json` per day.
3. **Combine + normalize.** Concatenate the batch's day JSONs into one `{days: [...]}` file. Normalize
   every `date` field and every `reporting_context[].retrieved` from `YYYY-MM-DD` to `YYYY/MM/DD` —
   the site's date parsing expects the slash format.
4. **Verify quotes**: `python3 tools/verify_quotes.py <batch_days.json>` → writes
   `<name>.verified.json`, reports kept/dropped quote counts and unconfirmed exhibit refs. Use the
   `.verified.json` output downstream, not the raw combine.
5. **Synthesize**: produce a cross-day `synthesis` object (people/orgs/events/edges/gaps/
   contradictions) either via an Agent call reading all the batch's day JSONs, or hand-written if
   agents are unavailable. **Be conservative about recurring high-profile figures** (e.g. Matlala,
   Witness F, Mkhwanazi, Sibiya) — only add/change their status entry if *this batch's own days* give
   a genuinely new, confident basis. See the STATUS_RANK warning below for why.
6. **Merge**: `python3 tools/merge_backfill.py --synthesis <isolated synthesis object file>`. Pass
   ONLY the bare `synthesis` object, never the `{days, synthesis}` wrapper — passing the wrapper
   silently merges nothing. This updates `days_raw.json` / `people_raw.json` (kept out of the repo,
   parent directory — these are working research payloads, not the published output).
7. **Build**: `python3 tools/build_data.py` (→ `data/*.json`), `python3 tools/make_pages.py`
   (→ `*.html`).
8. **Smoke test**: make sure `python3 -m http.server 8899` is running (restart it if `check.js`
   gets `ERR_CONNECTION_REFUSED`), then `node tools/check.js` — headless-Chromium check for console
   errors, 404s, external requests, mobile overflow.
9. **Commit locally** (`git add`/`git commit` in the sandbox — normal `Bash`, never `device_bash`,
   see constraints below). **Deliver**: `SendUserFile` the changed files, then
   `mcp__remote-devices__device_commit_files(force:true)` to write them into the user's local
   clone on their Mac.
10. Update `tools/BACKLOG.md`'s status section with what just shipped. If a batch spans a full
    day-range, note it in commit message and BACKLOG.

## Known infrastructure problems (check if still true before trusting this)

- **The `Workflow` tool is broken for this project as of 2026/08/27**: every subagent it spawns
  fails all tool calls (Read/Bash/Glob/Grep) with a permission-handler error, even though the
  identical script worked earlier in the project and a plain `Agent` call works fine in the same
  environment. Confirmed broken across multiple retries. **Workaround (current standing method)**:
  use `/home/claude/gen_prompt.py` to generate one self-contained prompt file per day in
  `/tmp/prompt_N.txt`, then fire multiple `Agent` tool calls **in one message** (not `Workflow`),
  each told to read its own prompt file and write its JSON output directly. Do the same for
  synthesis (one `Agent` call reading all the batch's day JSONs). If you retry `Workflow` and it
  works again, `tools/wf_extract_batch.js` is the reusable script — but don't burn a batch finding
  out; test with one throwaway day first.
- **`device_bash` must never run `git`**, not even read-only `git status`. It has left an
  unrecoverable `.git/index.lock` before. Use the sandbox's own `Bash` tool for all git operations;
  use `device_bash` only for filesystem operations on the user's Mac.
- **This cloud sandbox cannot push to GitHub** — outbound git/GitHub access is proxy-blocked. Commits
  happen locally in the sandbox and are also delivered to the user's Mac clone via
  `device_commit_files`; the user has to `git push` themselves from their machine. Remind them
  periodically that there's a growing stack of unpushed local commits.
- **`mcp__remote-devices__device_stage_files` has been persistently 403ing** with
  `untrusted_device` — this blocks pulling new source files (e.g. downloaded transcript PDFs) from
  the user's Mac into the sandbox. `device_commit_files` (pushing sandbox output back to the Mac)
  keeps working regardless. If staging fails, don't loop on it — tell the user the desktop app may
  need re-authenticating, and route around it (e.g. fetch transcripts directly from the Supabase API
  instead of relying on files the user already downloaded).
- **Account/session rate limits**: when hit mid-batch, check `date -u` against the stated reset
  time. If the reset has already passed, retry immediately. If not, use `send_later`/`create_trigger`
  (the Claude Code Remote MCP tools) to schedule a resume shortly after — **never the local `Cron*`
  tools**, which don't survive the session ending. Always ship whatever partial batch completed
  rather than discarding it ("salvage and ship").
- **`merge_backfill.py` status-downgrade risk**: it uses `STATUS_RANK` (lower rank = less severe)
  and the lower-ranked status wins on conflict when the same person appears in two batches. A vaguer
  synthesis entry in a later batch can silently overwrite an already well-evidenced status from an
  earlier one. Mitigated by omitting uncertain recurring-person entries from synthesis rather than
  guessing (see step 5 above) — keep doing this.

## Where things stand (update this section every session — check `tools/BACKLOG.md` too, it's the
more detailed/authoritative day-by-day log)

As of 2026/08/31: Days 1–15 (pilot), 17–89 are extracted, verified, merged, built and delivered
to the user's Mac — i.e. the entire 1–90 range is done except Day 14 (blocked, see below) and the
confirmed gaps. **Days 92–166 (69 days) are blocked**: their PDFs are already downloaded to the
user's Mac (`~/Downloads/mad-day-0NN.pdf`) but `mcp__remote-devices__device_stage_files` keeps
returning `untrusted_device` — re-confirmed again on 2026/08/31 with a single-file retry, per the
standing "retry once per session, don't loop" rule. **This needs the user to re-authenticate the
Claude desktop app on that Mac** before staging (and therefore any further extraction) can
proceed — ask once per session if it's still blocked, don't hammer it. Day 14 is blocked by the
same issue. Known genuinely-missing transcript days (no transcript media exists): 16, 56, 85, 90,
91, 104, 124, 125, 130, 131, 143 — don't keep trying these, they're recorded gaps. Nothing has
been pushed to GitHub yet — all commits are local to the sandbox and mirrored to the user's Mac
clone; there's a growing stack of local commits the user needs to `git push` themselves.

## Why CLAUDE.md, and what "best practice" means here

This file is read automatically by Claude Code–style tools (including this Agent SDK-based
session) at the start of a session when it's present at the repo root — that's the actual
mechanism, not a claude.ai-specific feature, which is why it works whether you're in a claude.ai
Project, a bare `claude` CLI session, or plain API billing with the SDK pointed at this repo. It
persists because it's a committed file in the repo, unlike claude.ai Project docs (which only
follow you inside that Project) or this conversation's own memory (which doesn't survive a new
session at all).

Best practice for a file like this: keep it to orientation and process, not a duplicate of
README.md's architecture docs or BACKLOG.md's day-by-day log — link to those instead of repeating
them. Keep the "where things stand" section current every session (it's the piece most likely to
rot). Keep the infrastructure-problem list honest — note when something is fixed rather than
leaving stale warnings. If this file starts drifting from BACKLOG.md, BACKLOG.md wins on specifics
(it's updated per-batch); this file wins on process and rules.
