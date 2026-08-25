#!/usr/bin/env python3
"""
Build the canonical /data layer for The Madlanga Tracker from research payloads.

Inputs (research output, kept out of the repo):
    ../days_raw.json    - sitting days
    ../people_raw.json  - people / orgs / events / edges

Outputs (committed):
    data/meta.json  data/days.json  data/people.json
    data/orgs.json  data/events.json data/edges.json data/gaps.json

Run:  python3 tools/build_data.py
"""
import json, os, re, sys, unicodedata
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.dirname(ROOT)
DATA = os.path.join(ROOT, "data")

SAST = timezone(timedelta(hours=2))

STATUS_LABELS = [
    "Testified",
    "Implicated (denied)",
    "Implicated (not yet responded)",
    "Implicated (untested)",
    "Criminally charged in a separate matter",
    "Commission official",
]

TIERS = {
    1: {"name": "EVIDENCE / Tier 1", "note": "The commission's own records, Parliament, SAFLII."},
    2: {"name": "Tier 2 - mainstream", "note": "SABC News, News24, TimesLIVE, EWN, IOL and comparable outlets."},
    3: {"name": "Tier 3 - investigative", "note": "Daily Maverick, amaBhungane, Mail & Guardian, GroundUp."},
    4: {"name": "Tier 4 - reference", "note": "Wikipedia and similar. Used only for biographical basics and photo licensing."},
}

WORKSTREAMS = [
    {"id": "kzn-pktt",              "label": "KZN policing & the PKTT",      "colour": "#e2725b"},
    {"id": "idac-npa",              "label": "IDAC & the NPA",               "colour": "#5b9bd5"},
    {"id": "matlala-saps-contract", "label": "The SAPS health contract",     "colour": "#c9a227"},
    {"id": "crime-intelligence",    "label": "Crime Intelligence",           "colour": "#7d9e5c"},
    {"id": "political-interference","label": "Political interference",       "colour": "#9b7bb8"},
]

EDGE_STRENGTHS = ["testified", "documented", "alleged", "denied"]


def slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "unknown"


def load(name):
    p = os.path.join(SRC, name)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def norm_source(s):
    """Normalise one source record. Drop anything without a real URL."""
    url = (s or {}).get("url")
    if not url or not str(url).startswith("http"):
        return None
    tier = s.get("tier")
    tier = int(tier) if tier in (1, 2, 3, 4, "1", "2", "3", "4") else 3
    return {
        "url": url,
        "tier": tier,
        "publisher": s.get("publisher") or "",
        "retrieved": (s.get("retrieved") or "").replace("-", "/"),
        "partial": bool(s.get("partial")),
    }


def norm_sources(lst):
    out = [norm_source(s) for s in (lst or [])]
    return [s for s in out if s]


def best_tier(sources):
    return min([s["tier"] for s in sources], default=None)


def main():
    days_raw   = load("days_raw.json")
    people_raw = load("people_raw.json")

    os.makedirs(DATA, exist_ok=True)
    gaps = []
    gid = 0

    def add_gap(desc, resolve, area):
        nonlocal gid
        gid += 1
        gaps.append({
            "id": f"gap-{gid:03d}",
            "area": area,
            "description": desc,
            "would_resolve": resolve,
            "logged": TODAY,
        })

    now = datetime.now(SAST)
    TODAY = now.strftime("%Y/%m/%d")

    # ---------------- days ----------------
    days = []
    for d in days_raw["days"]:
        n = d.get("day_number")
        srcs = norm_sources(d.get("sources"))
        rec = {
            "id": f"day-{n:03d}" if n else f"day-{slug(d['date'])}",
            "day_number": n,
            "day_number_verified": bool(d.get("day_number_verified")),
            "date": d["date"],
            "weekday": d.get("weekday"),
            "workstream": d.get("workstream"),
            "witnesses": [
                {
                    "person_id": slug(w["name"]),
                    "name": w["name"],
                    "role_as_described": w.get("role_as_described"),
                    "note": w.get("status_hint"),
                }
                for w in (d.get("witnesses") or [])
            ],
            "summary": d.get("summary"),
            "rulings": [
                {"description": r["description"], "source_url": r.get("source_url"), "tier_label": "RULING"}
                for r in (d.get("rulings") or [])
            ],
            "exhibits": d.get("exhibits") or [],
            "quotes": [
                {
                    "text": q["text"],
                    "speaker": q.get("speaker"),
                    "source_url": q.get("source_url"),
                    "tier_label": "REPORTING",
                    "words": len(q["text"].split()),
                }
                for q in (d.get("quotes") or [])
            ],
            "video_url": d.get("video_url"),
            "sources": srcs,
            "best_tier": best_tier(srcs),
            "partial_source": all(s["partial"] for s in srcs) if srcs else True,
            "unverified": d.get("unverified") or [],
            "reporting_context": [],
        }
        # Tier 2/3 news-research context, kept clearly separate from the transcript (Tier 1) summary.
        # Anything without a real URL and a Tier 2/3 label is dropped and logged, never silently kept.
        for rc in (d.get("reporting_context") or []):
            url = (rc.get("url") or rc.get("source_url") or "")
            claim = rc.get("claim")
            tier = rc.get("tier")
            tier = int(tier) if tier in (2, 3, "2", "3") else None
            if not claim or not url or not str(url).startswith("http") or tier is None:
                add_gap(f"Day {n}: a reporting-context item was dropped for missing a claim, a real URL, "
                        f"or a valid Tier 2/3 label.",
                        "Re-source that claim against a whitelisted Tier 2 or Tier 3 outlet.", f"day-{n}")
                continue
            rec["reporting_context"].append({
                "claim": claim, "url": url, "publisher": rc.get("publisher") or "",
                "tier": tier, "retrieved": (rc.get("retrieved") or "").replace("-", "/"),
                "partial": bool(rc.get("partial")),
            })
        # enforce the 15-word quote ceiling
        for q in rec["quotes"]:
            if q["words"] >= 15:
                add_gap(f"Quote on day {n} exceeds the 15-word ceiling and was dropped: {q['speaker']}",
                        "Replace with a paraphrase or a shorter verbatim extract from the transcript.", "copyright")
        rec["quotes"] = [q for q in rec["quotes"] if q["words"] < 15]
        days.append(rec)
        for u in rec["unverified"]:
            add_gap(u, "Commission transcript or ruling for this sitting day.", f"day-{n}")

    days.sort(key=lambda r: r["date"], reverse=True)

    # ---------------- people ----------------
    appearances = {}
    for d in days:
        for w in d["witnesses"]:
            appearances.setdefault(w["person_id"], []).append(d["day_number"])

    people = []
    for p in people_raw["people"]:
        pid = p.get("id") or slug(p["name"])
        status = p.get("status")
        if status not in STATUS_LABELS:
            add_gap(f"Person '{p.get('name')}' carried a status label outside the closed list ({status!r}); "
                    f"defaulted to 'Implicated (untested)'.",
                    "Confirm the correct label against commission records.", "status-label")
            status = "Implicated (untested)"
        srcs = norm_sources(p.get("sources"))
        linked = sorted(set(appearances.get(pid, []) + appearances.get(slug(p["name"]), [])), reverse=True)
        rec = {
            "id": pid,
            "name": p["name"],
            "initials": "".join(w[0] for w in re.sub(r"[^A-Za-z '-]", "", p["name"]).split()[:2]).upper(),
            "role": p.get("role"),
            "status": status,
            "status_reason": p.get("status_reason"),
            "bio": p.get("bio"),
            "first_appearance": (p.get("first_appearance_date") or None),
            "linked_days": linked,
            "photo_url": p.get("photo_url"),
            "photo_source": p.get("photo_source"),
            "photo_licence": p.get("photo_licence"),
            "sources": srcs,
            "best_tier": best_tier(srcs),
            "unverified": p.get("unverified") or [],
        }
        if not rec["photo_url"]:
            rec["photo_mode"] = "initials"
        else:
            rec["photo_mode"] = "image"
        people.append(rec)

    known_people = {p["id"] for p in people}

    # witnesses named in days but absent from the roster
    for d in days:
        for w in d["witnesses"]:
            if w["person_id"] not in known_people:
                people.append({
                    "id": w["person_id"], "name": w["name"],
                    "initials": "".join(x[0] for x in re.sub(r"[^A-Za-z '-]", "", w["name"]).split()[:2]).upper(),
                    "role": w.get("role_as_described"), "status": "Testified",
                    "status_reason": f"Gave evidence before the commission on day {d['day_number']}.",
                    "bio": None, "first_appearance": d["date"],
                    "linked_days": sorted(set(appearances.get(w["person_id"], [])), reverse=True),
                    "photo_url": None, "photo_source": None, "photo_licence": None,
                    "photo_mode": "initials", "sources": d["sources"], "best_tier": d["best_tier"],
                    "unverified": ["No standalone biographical profile assembled yet."],
                })
                known_people.add(w["person_id"])
                add_gap(f"No biography or photo for {w['name']}, who appears as a witness in the sample days.",
                        "A profile assembled from the commission's witness statement index.", "people")

    people.sort(key=lambda p: p["name"])

    photoless = [p["name"] for p in people if not p["photo_url"]]
    if photoless:
        add_gap(f"No freely-licensed photograph located for {len(photoless)} of {len(people)} people; "
                f"all render as initials avatars.",
                "Wikimedia Commons uploads, or official commission portraits released under a reusable licence.",
                "photos")

    # ---------------- orgs / events ----------------
    orgs = []
    for o in people_raw["orgs"]:
        srcs = norm_sources(o.get("sources"))
        orgs.append({"id": o.get("id") or slug(o["name"]), "name": o["name"], "type": o.get("type"),
                     "description": o.get("description"), "sources": srcs, "best_tier": best_tier(srcs)})
    orgs.sort(key=lambda o: o["name"])

    events = []
    for e in people_raw["events"]:
        srcs = norm_sources(e.get("sources"))
        events.append({"id": e.get("id") or slug(e["title"]), "title": e["title"],
                       "date": (e.get("date") or None), "description": e.get("description"),
                       "sources": srcs, "best_tier": best_tier(srcs)})
    events.sort(key=lambda e: (e["date"] or "0000/00/00"))

    # ---------------- edges ----------------
    node_ids = known_people | {o["id"] for o in orgs} | {e["id"] for e in events}
    edges, dropped = [], 0
    for i, ed in enumerate(people_raw["edges"], 1):
        f, t = ed.get("from"), ed.get("to")
        srcs = norm_sources(ed.get("sources"))
        strength = ed.get("strength")
        if f not in node_ids or t not in node_ids:
            dropped += 1
            continue
        if strength not in EDGE_STRENGTHS or not srcs:
            dropped += 1
            continue
        edges.append({"id": f"edge-{i:03d}", "from": f, "to": t, "type": ed.get("type"),
                      "strength": strength, "date": ed.get("date") or None,
                      "sources": srcs, "best_tier": best_tier(srcs)})
    if dropped:
        add_gap(f"{dropped} relationship(s) were dropped from edges.json: either an endpoint was not in the "
                f"node set, the strength was outside the closed list, or no source URL survived validation.",
                "Re-derive those relationships from commission evidence with citations.", "edges")

    for g in days_raw.get("gaps", []):
        add_gap(g["description"], g["would_resolve"], "days")
    for g in people_raw.get("gaps", []):
        add_gap(g["description"], g["would_resolve"], "people")

    meta = {
        "site": "The Madlanga Tracker",
        "commission": "Judicial Commission of Inquiry into Criminality, Political Interference and "
                      "Corruption in the Criminal Justice System",
        "chair": "Retired Justice Mbuyiseli Madlanga",
        "phase": "Phase 1 - scaffold. Sample data only: the ten most recent sitting days.",
        "last_updated": now.strftime("%Y/%m/%d %H:%M") + " SAST",
        "latest_day": days_raw.get("latest_day_number"),
        "latest_day_date": days_raw.get("latest_day_date"),
        "latest_day_verified": next((d["day_number_verified"] for d in days
                                     if d["day_number"] == days_raw.get("latest_day_number")), False),
        "days_in_data": len(days),
        "days_outstanding": (days_raw.get("latest_day_number") or 0) - len(days),
        "status_labels": STATUS_LABELS,
        "tiers": {str(k): v for k, v in TIERS.items()},
        "workstreams": WORKSTREAMS,
        "edge_strengths": EDGE_STRENGTHS,
        "counts": {"days": len(days), "people": len(people), "orgs": len(orgs),
                   "events": len(events), "edges": len(edges), "gaps": len(gaps)},
        "method_note": days_raw.get("notes_on_method"),
    }

    for name, payload in [("meta", meta), ("days", days), ("people", people),
                          ("orgs", orgs), ("events", events), ("edges", edges), ("gaps", gaps)]:
        with open(os.path.join(DATA, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(f"  data/{name}.json  ({len(payload) if isinstance(payload, list) else 'object'})")

    print(f"\nDays {len(days)} | People {len(people)} | Orgs {len(orgs)} | "
          f"Events {len(events)} | Edges {len(edges)} | Gaps {len(gaps)}")


if __name__ == "__main__":
    main()
