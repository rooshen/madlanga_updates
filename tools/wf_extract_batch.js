export const meta = {
  name: 'madlanga-backfill-batch',
  description: 'Per-day transcript extraction + Tier2/3 news research, then cross-day synthesis',
  phases: [
    { title: 'Extract' },
    { title: 'Synthesize' },
  ],
}

const RULES = `You are building one sitting-day record for "The Madlanga Tracker", a tracker for South
Africa's Judicial Commission of Inquiry into Criminality, Political Interference and Corruption in
the Criminal Justice System (chaired by retired Justice Mbuyiseli Madlanga).

THIS IS A COMMISSION OF INQUIRY, NOT A CRIMINAL TRIAL. Never use: accused, charges, verdict, guilty,
defendant. Always prefer: witness, implicated person, evidence leader, testimony, ruling, finding.

Every named person mentioned must be describable with exactly one status from this closed list
(you do not assign status here, just describe facts precisely so a later step can):
Testified / Implicated (denied) / Implicated (not yet responded) / Implicated (untested) /
Criminally charged in a separate matter / Commission official.

QUOTES: any direct quote you extract, from the transcript OR from a news article, must be under 15
words, in quotation marks, with a speaker/attribution. Prefer paraphrase over quoting. Never invent
a quote — every quote must be an exact substring of its source (this will be verified by a script,
not trusted from you).

NO FABRICATION: if you cannot find something in the transcript, do not guess. Leave it out or note
it in "unverified". Every factual claim must trace to a real source.

SOURCE TIERS for reporting_context (do NOT use these for the main transcript-derived summary/quotes,
which are Tier 1 / EVIDENCE by definition):
  Tier 2 (mainstream): SABC News, News24, TimesLIVE, EWN, IOL
  Tier 3 (investigative): Daily Maverick, amaBhungane, Mail & Guardian, GroundUp
Only use these whitelisted outlets. A reporting_context claim must read as REPORTED, not as
established fact — do not let Tier 2/3 reporting bleed into the EVIDENCE-tier summary as if it were
transcript fact. If you can't find genuine contemporaneous coverage of this specific sitting day,
leave reporting_context empty — do not pad it with generic background pieces.`

const DAY_SCHEMA = {
  type: 'object',
  properties: {
    day_number: { type: 'integer' },
    date: { type: 'string' },
    weekday: { type: 'string' },
    workstream: { type: 'string', enum: ['kzn-pktt', 'idac-npa', 'matlala-saps-contract', 'crime-intelligence', 'political-interference'] },
    venue: { type: 'string' },
    evidence_leaders: { type: 'array', items: { type: 'string' } },
    witnesses: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          role_as_described: { type: 'string' },
          protected_identity: { type: 'boolean' },
          sworn: { type: 'boolean' },
        },
        required: ['name'],
      },
    },
    summary: { type: 'string', description: '2-4 neutral sentences on what happened this sitting day' },
    rulings: { type: 'array', items: { type: 'object', properties: { description: { type: 'string' }, by: { type: 'string' } }, required: ['description'] } },
    exhibits: { type: 'array', items: { type: 'object', properties: { ref: { type: 'string' }, description: { type: 'string' } } } },
    quotes: { type: 'array', items: { type: 'object', properties: { text: { type: 'string' }, speaker: { type: 'string' } }, required: ['text'] } },
    key_points: { type: 'array', items: { type: 'string' } },
    loose_ends: { type: 'array', items: { type: 'string' } },
    unverified: { type: 'array', items: { type: 'string' } },
    protected_identity_notes: { type: 'array', items: { type: 'string' } },
    header_line: { type: 'string', description: 'The exact day-header text as it appears at the top of the transcript, e.g. "DAY 17"' },
    reporting_context: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          url: { type: 'string' },
          publisher: { type: 'string' },
          tier: { type: 'integer', enum: [2, 3] },
          retrieved: { type: 'string' },
          partial: { type: 'boolean' },
        },
        required: ['claim', 'url', 'publisher', 'tier'],
      },
    },
  },
  required: ['day_number', 'date', 'summary', 'header_line', 'witnesses', 'evidence_leaders'],
}

const SYNTH_SCHEMA = {
  type: 'object',
  properties: {
    people: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          role: { type: 'string' },
          status: { type: 'string', enum: ['Testified', 'Implicated (denied)', 'Implicated (not yet responded)', 'Implicated (untested)', 'Criminally charged in a separate matter', 'Commission official'] },
          status_reason: { type: 'string' },
          protected_identity: { type: 'boolean' },
        },
        required: ['name', 'status'],
      },
    },
    orgs: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, type: { type: 'string' }, description: { type: 'string' } }, required: ['name'] } },
    events: { type: 'array', items: { type: 'object', properties: { title: { type: 'string' }, date: { type: 'string' }, description: { type: 'string' } }, required: ['title'] } },
    edges: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          from: { type: 'string' }, to: { type: 'string' }, type: { type: 'string' },
          strength: { type: 'string', enum: ['testified', 'documented', 'alleged', 'denied'] },
          date: { type: 'string' },
        },
        required: ['from', 'to', 'strength'],
      },
    },
    gaps: { type: 'array', items: { type: 'object', properties: { description: { type: 'string' }, would_resolve: { type: 'string' } }, required: ['description', 'would_resolve'] } },
    contradictions: { type: 'array', items: { type: 'object', properties: { description: { type: 'string' }, days: { type: 'array', items: { type: 'integer' } }, confidence: { type: 'string' } }, required: ['description'] } },
  },
}

function extractPrompt(d) {
  return `${RULES}

Read the transcript at ${d.transcript_path} (use the Read tool; it may be long — read it in full).

Known hints (verify against the transcript itself, transcript wins if they disagree):
  Day number: ${d.day_number}
  Date hint: ${d.date_hint || 'not known, read the transcript header'}
  Witness hint: ${d.witness_hint || 'not known, read the transcript'}
  Evidence leader hint: ${d.el_hint || 'not known, read the transcript'}

Then do ONE targeted web search for contemporaneous Tier 2/3 news coverage of this specific sitting
day (try something like "Madlanga Commission Day ${d.day_number}" or "Madlanga Commission" plus the
witness's name and the date). Only keep results from: SABC News, News24, TimesLIVE, EWN, IOL, Daily
Maverick, amaBhungane, Mail & Guardian, GroundUp. If nothing genuinely relevant turns up, leave
reporting_context empty rather than forcing an unrelated result in.

Produce the day record via the required structured output. header_line must be copied verbatim from
where the transcript itself prints its day number (e.g. "DAY 17").`
}

function synthPrompt(days) {
  return `${RULES}

Below are ${days.length} extracted sitting-day records (JSON) from consecutive days of the same
commission. Synthesize a cross-day view:

- people: every named witness, implicated person, or commission official across all days, each with
  exactly one status from the closed list and a one-line status_reason grounded in what the day
  records actually say. Mark protected_identity true for anonymised witnesses (e.g. "Witness D").
- orgs: organisations named (SAPS, NPA, IDAC, specific units, etc.)
- events: any discrete named event referenced (e.g. a specific incident, a raid, a meeting) with a
  date if known.
- edges: relationships between people/orgs/events evidenced across these days (who implicated whom,
  who reports to whom, who was present at what) — each needs a strength from
  testified/documented/alleged/denied.
- gaps: anything you noticed was thin, unconfirmed, or inconsistent across days that a future
  research pass should resolve.
- contradictions: any place two days (or a day and reporting_context) disagree on a fact, with which
  days are involved and your confidence that it's a genuine contradiction vs. just incomplete info.

Day records:
${JSON.stringify(days, null, 1)}`
}

const batchDays = args.days
const extracted = await pipeline(
  batchDays,
  d => agent(extractPrompt(d), { label: `day-${d.day_number}`, phase: 'Extract', schema: DAY_SCHEMA })
)

const clean = extracted.filter(Boolean)
log(`Extracted ${clean.length}/${batchDays.length} days`)

const synthesis = await agent(synthPrompt(clean), { label: 'synthesis', phase: 'Synthesize', effort: 'xhigh', schema: SYNTH_SCHEMA })

return { days: clean, synthesis }
