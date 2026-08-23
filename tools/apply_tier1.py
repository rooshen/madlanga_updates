#!/usr/bin/env python3
"""
Patch days_raw.json with Tier 1 facts read from the commission's own hearings index
(criminaljusticecommission.org.za/hearings and /hearings/YYYY/MM/DD), retrieved
2026/08/22 through a rendered browser session.

Only fields actually shown on the commission's own pages are written here.
Where Tier 1 and Tier 2/3 conflict, BOTH are kept and the conflict is logged.
"""
import json, os

SRC = "/home/claude/days_raw.json"
BASE = "https://criminaljusticecommission.org.za/hearings/"
RET = "2026/08/22"

# Verbatim from the commission's own hearings index.
TIER1 = {
    163: {"date": "2026/08/20", "weekday": "Thursday", "witness_line": "Mr Fadiel Adams MP.",
          "leaders": ["Adv Segeels Ncube"], "materials": ["Audio", "Transcript"], "path": "2026/08/20"},
    162: {"date": "2026/08/19", "weekday": "Wednesday", "witness_line": "Mr Fadiel Adams MP.",
          "leaders": ["Adv Segeels Ncube"], "materials": ["2 materials"], "path": "2026/08/19"},
    161: {"date": "2026/08/18", "weekday": "Tuesday",
          "witness_line": "None (the scheduled witness, Mr Vusimuzi Matlala, was postponed)",
          "leaders": ["Adv Chaskalson SC"], "materials": ["1 material"], "path": "2026/08/18"},
    160: {"date": "2026/08/17", "weekday": "Monday", "witness_line": "Mr Vusimuzi Matlala.",
          "leaders": ["Adv Sello SC", "Adv Hassim SC"], "materials": ["2 materials"], "path": "2026/08/17"},
    159: {"date": "2026/08/14", "weekday": "Friday", "witness_line": "Mr Carrim.",
          "leaders": ["Adv Hassim SC", "Adv Premhid"], "materials": ["2 materials"], "path": "2026/08/14"},
    158: {"date": "2026/08/13", "weekday": "Thursday", "witness_line": "Mr Gregory Loftus.",
          "leaders": ["Adv Sikhakhane SC"], "materials": ["2 materials"], "path": "2026/08/13"},
    157: {"date": "2026/08/12", "weekday": "Wednesday", "witness_line": "Mr Len Barnabas John.",
          "leaders": ["Adv Chaskalson SC"], "materials": ["2 materials"], "path": "2026/08/12"},
    156: {"date": "2026/08/11", "weekday": "Tuesday", "witness_line": "Ms Ramsamy.",
          "leaders": ["Adv Segeels Ncube"], "materials": ["2 materials"], "path": "2026/08/11"},
    155: {"date": "2026/08/06", "weekday": "Thursday", "witness_line": "Matthew Sesoko.",
          "leaders": ["Advocate Pooe"], "materials": ["2 materials"], "path": "2026/08/06"},
}

# Days the commission's index lists that this scaffold does not yet hold.
NOT_YET_HELD = [
    {"day": 154, "date": "2026/08/05", "witness": "Drushantha Ramsamy", "leader": "Adv Segeels Ncube"},
    {"day": 153, "date": "2026/08/04", "witness": "Adv Peter Serunye", "leader": "Adv Pooe"},
]

CONFLICTS = [
    {"day": 159,
     "tier1": "The commission's own hearings index records the Day 159 witness as 'Mr Carrim', with evidence "
              "leaders Adv Hassim SC and Adv Premhid.",
     "other": "Tier 2 and Tier 3 reporting (TimesLIVE, Daily Maverick) says Carrim did NOT appear on 14 August "
              "and that the commission resolved to set a criminal process in motion over his non-compliance; a "
              "Sunday World item places Adv Drushantha Ramsamy at the commission that day. Adv Premhid is "
              "described in reporting as Carrim's counsel, not an evidence leader.",
     "resolution": "Unresolved. The commission's index may be recording whose matter was before it rather than "
                   "who took the stand. Both readings are held; neither is presented as settled.",
     "would_resolve": "The Day 159 transcript, downloadable from the commission's own page for 2026/08/14."},
    {"day": 164,
     "tier1": "The commission's own hearings index does NOT list a Day 164. Its most recent August entry is "
              "Day 163 on 20 August 2026.",
     "other": "SABC News, SABC+ and YouTube all carry 'Day 164' material dated Friday 21 August 2026, and "
              "Tier 2/3 reporting describes Adams continuing his evidence that day.",
     "resolution": "A sitting on 21 August is well attested. Whether it is numbered 164 is not confirmed by "
                   "Tier 1, most likely because the commission's index had not yet been updated when it was read.",
     "would_resolve": "Re-reading the commission's hearings index after it publishes the 21 August entry."},
]


def main():
    doc = json.load(open(SRC, encoding="utf-8"))
    changed = []

    for d in doc["days"]:
        n = d.get("day_number")
        t = TIER1.get(n)
        if not t:
            if n == 164:
                d["day_number_verified"] = False
                d["tier1"] = {"listed": False,
                              "note": "Not listed on the commission's hearings index as at 2026/08/22. "
                                      "The sitting on 21 August 2026 is attested by Tier 2 broadcasters; "
                                      "the day number is not confirmed by Tier 1."}
                d.setdefault("unverified", []).insert(
                    0, "The commission's own hearings index does not list a Day 164. The 21 August sitting is "
                       "attested by SABC and YouTube material; the number is not Tier 1 confirmed.")
                changed.append("164: day number downgraded to unverified (absent from Tier 1 index)")
            continue

        url = BASE + t["path"]
        assert d["date"] == t["date"], f"date mismatch on day {n}: {d['date']} vs {t['date']}"

        if not d["day_number_verified"]:
            d["day_number_verified"] = True
            changed.append(f"{n}: day number CONFIRMED against the commission's own index")

        d["evidence_leaders"] = t["leaders"]
        d["tier1"] = {"listed": True, "url": url, "witness_line": t["witness_line"],
                      "evidence_leaders": t["leaders"], "materials": t["materials"],
                      "retrieved": RET,
                      "note": "Read from the commission's own hearings index in a rendered browser session. "
                              "Full transcripts and audio are downloadable from this page."}
        d["sources"].insert(0, {"url": url, "tier": 1,
                                "publisher": "Judicial Commission of Inquiry — official hearings index",
                                "retrieved": RET, "partial": False})
        changed.append(f"{n}: Tier 1 source added; evidence leaders {', '.join(t['leaders'])}")

        # drop the now-answered evidence-leader gaps
        before = len(d.get("unverified", []))
        d["unverified"] = [u for u in d.get("unverified", [])
                           if "evidence leader" not in u.lower() and "Evidence leader" not in u]
        if len(d["unverified"]) != before:
            changed.append(f"{n}: evidence-leader gap closed by Tier 1")

    # record conflicts on the affected days
    for c in CONFLICTS:
        for d in doc["days"]:
            if d.get("day_number") == c["day"]:
                d.setdefault("conflicts", []).append(c)
                d.setdefault("unverified", []).append(
                    f"TIER 1 / TIER 2 CONFLICT — {c['tier1']} {c['other']} {c['resolution']}")
                changed.append(f"{c['day']}: conflict recorded")

    doc["tier1_index"] = {
        "url": "https://criminaljusticecommission.org.za/hearings",
        "retrieved": RET,
        "note": "The commission publishes a per-day index with witness, evidence leader, audio and full "
                "transcript at /hearings/YYYY/MM/DD. It is JavaScript-rendered, so it is reachable only "
                "through a real browser session, not a plain fetch.",
        "days_listed_not_yet_held": NOT_YET_HELD,
    }

    # gaps this resolves, and gaps it creates
    doc["gaps"] = [g for g in doc["gaps"] if not (
        "Day 160 could not be pinned" in g["description"]
        or "could not be used as a Tier 1 source" in g["description"]
        or "Day numbering is not internally consistent" in g["description"]
        or "Evidence leader attributions are thin" in g["description"]
        or "No Tier 1 source underpins any" in g["description"])]

    doc["gaps"] = [
        {"description": "Tier 1 transcripts and audio exist for every sitting day and are downloadable from the "
                        "commission's own per-day pages, but none has yet been read. Every day summary on this "
                        "site still rests on Tier 2/3 reporting.",
         "would_resolve": "Downloading and reading the per-day transcripts, which would move day summaries, "
                          "quotations and exhibit references from REPORTING to EVIDENCE."},
        {"description": "The commission's index lists Day 154 (2026/08/05, Drushantha Ramsamy) and Day 153 "
                        "(2026/08/04, Adv Peter Serunye), which this scaffold does not hold. The sample of ten "
                        "days is therefore Days 155–164 by broadcaster numbering, which Tier 1 only confirms to 163.",
         "would_resolve": "Phase 2 back-fill from Day 1."},
    ] + doc["gaps"]

    for c in CONFLICTS:
        doc["gaps"].insert(0, {
            "description": f"Day {c['day']} — Tier 1 and Tier 2/3 conflict. {c['tier1']} {c['other']} {c['resolution']}",
            "would_resolve": c["would_resolve"]})

    doc["notes_on_method"] = (
        "TIER 1 REACHED 2026/08/22. The commission's own hearings index is a JavaScript-rendered application "
        "and returns an empty shell to a plain fetch; it was read through a rendered browser session instead. "
        "It publishes, per sitting day, the witness, the evidence leader, downloadable audio and a full "
        "transcript, at /hearings/YYYY/MM/DD. That confirmed the date and number of Days 155–163, supplied "
        "evidence-leader names for all nine, and corrected two things this scaffold had wrong: Day 160 was "
        "recorded as inferred and is now confirmed, and Day 164 was recorded as confirmed but is absent from "
        "the commission's index, so its number is now marked unverified. Two Tier 1 / Tier 2 conflicts are "
        "recorded rather than resolved — the Day 159 witness, and the existence of a Day 164. No transcript "
        "has been read yet, so every day summary here remains Tier 2/3 REPORTING. "
    ) + doc.get("notes_on_method", "")

    json.dump(doc, open(SRC, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("Patched days_raw.json\n")
    for c in changed:
        print("  " + c)


if __name__ == "__main__":
    main()
