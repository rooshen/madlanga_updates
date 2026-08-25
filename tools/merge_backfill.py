#!/usr/bin/env python3
"""
Merge a verified Phase 2 back-fill batch into the research payloads that build_data.py consumes.

Appends rather than rewrites: existing days are left alone unless --replace is given, people are
merged by slug with the fuller record winning, edges are deduplicated on (from, to, type, strength).

Usage:
  python3 tools/merge_backfill.py batch.verified.json --synthesis synth.json [--replace]
"""
import argparse, json, os, re, unicodedata

SRC = "/home/claude"
DAYS_RAW = os.path.join(SRC, "days_raw.json")
PEOPLE_RAW = os.path.join(SRC, "people_raw.json")
RET = "2026/08/23"
TX_URL = "https://criminaljusticecommission.org.za/hearings/{}"

STATUS_RANK = {  # if two sources disagree, the label claiming LESS wins
    "Commission official": 0, "Testified": 1, "Implicated (untested)": 2,
    "Implicated (not yet responded)": 3, "Implicated (denied)": 4,
    "Criminally charged in a separate matter": 5,
}


def slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower() or "unknown"


def tier1_source(date):
    return {"url": TX_URL.format(date.replace("/", "/")), "tier": 1,
            "publisher": "Judicial Commission of Inquiry — official transcript",
            "retrieved": RET, "partial": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--synthesis", required=True)
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()

    batch = json.load(open(a.batch, encoding="utf-8"))
    batch = batch["days"] if isinstance(batch, dict) and "days" in batch else batch
    synth = json.load(open(a.synthesis, encoding="utf-8"))

    days_doc = json.load(open(DAYS_RAW, encoding="utf-8"))
    people_doc = json.load(open(PEOPLE_RAW, encoding="utf-8"))

    have = {d.get("day_number") for d in days_doc["days"]}
    added = replaced = 0

    for r in batch:
        n = r.get("day_number")
        rec = {
            "day_number": n,
            "day_number_verified": True,          # read off the commission's own transcript header
            "date": r["date"],
            "weekday": r.get("weekday"),
            "workstream": r.get("workstream"),
            "venue": r.get("venue"),
            "evidence_leaders": r.get("evidence_leaders") or [],
            "witnesses": [{"name": w["name"], "role_as_described": w.get("role_as_described"),
                           "status_hint": "testified", "protected_identity": bool(w.get("protected_identity")),
                           "sworn": w.get("sworn")} for w in (r.get("witnesses") or [])],
            "summary": r.get("summary"),
            "rulings": [{"description": x["description"], "source_url": TX_URL.format(r["date"]),
                         "by": x.get("by")} for x in (r.get("rulings") or [])],
            "exhibits": r.get("exhibits") or [],
            "quotes": [{"text": q["text"], "speaker": q.get("speaker"),
                        "source_url": TX_URL.format(r["date"]), "verified_verbatim": True}
                       for q in (r.get("quotes") or [])],
            "video_url": None,
            "sources": [tier1_source(r["date"])],
            "unverified": r.get("unverified") or [],
            "loose_ends": r.get("loose_ends") or [],
            "key_points": r.get("key_points") or [],
            "protected_identity_notes": r.get("protected_identity_notes") or [],
            "tier1": {"listed": True, "url": TX_URL.format(r["date"]),
                      "materials": ["Transcript"], "retrieved": RET,
                      "note": "Summary, rulings, exhibits and quotations extracted from the commission's own "
                              "published transcript. Quotations were verified as exact substrings of that "
                              "transcript by script, not by a model."},
            "evidence_grade": "EVIDENCE",
            "quote_verification": r.get("quote_verification"),
            "transcript_pages": r.get("transcript_pages"),
            "reporting_context": r.get("reporting_context") or [],
        }
        if n in have:
            if a.replace:
                days_doc["days"] = [rec if d.get("day_number") == n else d for d in days_doc["days"]]
                replaced += 1
            continue
        days_doc["days"].append(rec)
        added += 1

    days_doc["days"].sort(key=lambda d: d["date"], reverse=True)

    # ---- people ----
    by_id = {p["id"]: p for p in people_doc["people"]}
    p_added = p_merged = 0
    for p in synth.get("people", []):
        pid = slug(p["name"])
        new_status = p.get("status")
        if pid in by_id:
            cur = by_id[pid]
            # the label claiming less wins, except never downgrade a real "Testified"
            if STATUS_RANK.get(new_status, 9) < STATUS_RANK.get(cur.get("status"), 9):
                cur["status"] = new_status
                cur["status_reason"] = p.get("status_reason") or cur.get("status_reason")
            if not cur.get("role") and p.get("role"):
                cur["role"] = p["role"]
            cur.setdefault("sources", []).append(tier1_source(days_doc["days"][-1]["date"]))
            cur["protected_identity"] = bool(p.get("protected_identity")) or cur.get("protected_identity", False)
            p_merged += 1
        else:
            by_id[pid] = {
                "id": pid, "name": p["name"], "role": p.get("role"), "status": new_status,
                "status_reason": p.get("status_reason"), "bio": None,
                "first_appearance_date": None,
                "protected_identity": bool(p.get("protected_identity")),
                "photo_url": None, "photo_source": None, "photo_licence": None,
                "sources": [tier1_source(days_doc["days"][-1]["date"])],
                "unverified": ["Profile assembled from transcript extraction only; no biography written yet."],
            }
            p_added += 1
    people_doc["people"] = sorted(by_id.values(), key=lambda x: x["name"])

    # ---- orgs / events ----
    o_by = {slug(o["name"]): o for o in people_doc["orgs"]}
    o_added = 0
    for o in synth.get("orgs", []):
        k = slug(o["name"])
        if k not in o_by:
            o_by[k] = {"id": k, "name": o["name"], "type": o.get("type"),
                       "description": o.get("description"),
                       "sources": [tier1_source(days_doc["days"][-1]["date"])]}
            o_added += 1
    people_doc["orgs"] = sorted(o_by.values(), key=lambda x: x["name"])

    e_by = {slug(e["title"]): e for e in people_doc["events"]}
    e_added = 0
    for e in synth.get("events", []):
        k = slug(e["title"])
        if k not in e_by:
            e_by[k] = {"id": k, "title": e["title"], "date": e.get("date"),
                       "description": e.get("description"),
                       "sources": [tier1_source(days_doc["days"][-1]["date"])]}
            e_added += 1
    people_doc["events"] = sorted(e_by.values(), key=lambda x: (x["date"] or "0000/00/00"))

    # ---- edges ----
    seen = {(slug(x.get("from")), slug(x.get("to")), (x.get("type") or "").lower()) for x in people_doc["edges"]}
    ed_added = 0
    for e in synth.get("edges", []):
        key = (slug(e["from"]), slug(e["to"]), (e.get("type") or "").lower())
        if key in seen:
            continue
        seen.add(key)
        people_doc["edges"].append({
            "from": slug(e["from"]), "to": slug(e["to"]), "type": e.get("type"),
            "strength": e.get("strength"), "date": e.get("date"),
            "sources": [tier1_source(days_doc["days"][-1]["date"])]})
        ed_added += 1

    # ---- gaps + contradictions ----
    for g in synth.get("gaps", []):
        days_doc["gaps"].insert(0, {"description": g["description"], "would_resolve": g["would_resolve"]})
    for c in synth.get("contradictions", []):
        days_doc["gaps"].insert(0, {
            "description": f"CONTRADICTION ({c.get('confidence','?')} confidence, "
                           f"days {', '.join(map(str, c.get('days') or []))}): {c['description']}",
            "would_resolve": "Re-reading the relevant transcript passages side by side, or the commission's "
                             "own resolution of the point."})

    json.dump(days_doc, open(DAYS_RAW, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(people_doc, open(PEOPLE_RAW, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    print(f"days      +{added} added, {replaced} replaced  (total {len(days_doc['days'])})")
    print(f"people    +{p_added} added, {p_merged} merged   (total {len(people_doc['people'])})")
    print(f"orgs      +{o_added}   (total {len(people_doc['orgs'])})")
    print(f"events    +{e_added}   (total {len(people_doc['events'])})")
    print(f"edges     +{ed_added}  (total {len(people_doc['edges'])})")
    print(f"gaps      +{len(synth.get('gaps', []))} gaps, +{len(synth.get('contradictions', []))} contradictions")


if __name__ == "__main__":
    main()
