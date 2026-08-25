#!/usr/bin/env python3
"""
Deterministic quote verification against the official transcripts.

No model is trusted with this. Every quote extracted from a sitting day must be an exact
substring of that day's transcript once whitespace is normalised, and must be under the
15-word house ceiling. Anything that fails is DELETED and logged as a gap.

Usage:  python3 tools/verify_quotes.py <extracted.json> [--transcripts DIR] [--out verified.json]

Exit code 0 always — failing quotes are a data-quality signal, not a build error.
"""
import argparse, json, os, re, sys, unicodedata

DEFAULT_TX = "/home/claude/transcripts"
MAX_WORDS = 15


def norm(s: str) -> str:
    """Collapse whitespace and normalise the quote marks and dashes typists vary on."""
    s = unicodedata.normalize("NFKC", s or "")
    s = (s.replace("‘", "'").replace("’", "'")
          .replace("“", '"').replace("”", '"')
          .replace("–", "-").replace("—", "-")
          .replace(" ", " "))
    return re.sub(r"\s+", " ", s).strip()


def load_transcript(day: int, tx_dir: str):
    p = os.path.join(tx_dir, f"mad-day-{day:03d}.txt")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as f:
        return norm(f.read()).lower()


def check_day(rec: dict, tx_dir: str):
    """Returns (kept_quotes, failures[]). Mutates nothing."""
    day = rec.get("day_number")
    body = load_transcript(day, tx_dir)
    kept, fails = [], []

    for q in rec.get("quotes") or []:
        text = q.get("text") or ""
        words = len(text.split())
        nq = norm(text)

        if words >= MAX_WORDS:
            fails.append({"day": day, "reason": "over the 15-word ceiling",
                          "words": words, "speaker": q.get("speaker"), "text": text})
            continue
        if not nq:
            fails.append({"day": day, "reason": "empty quote", "speaker": q.get("speaker"), "text": text})
            continue
        if body is None:
            fails.append({"day": day, "reason": "no transcript on disk to check against",
                          "speaker": q.get("speaker"), "text": text})
            continue
        if nq.lower() not in body:
            fails.append({"day": day, "reason": "NOT a verbatim substring of the transcript",
                          "words": words, "speaker": q.get("speaker"), "text": text})
            continue

        q = dict(q)
        q["verified_verbatim"] = True
        q["words"] = words
        q["tier_label"] = "EVIDENCE"
        kept.append(q)

    return kept, fails


def split_ref(ref: str):
    """A ref field may be a compound like 'SFM1-SFM12' or 'WB1/WB2 (annexures)' — check each
    plausible exhibit token on its own rather than the whole decorated string at once."""
    ref = re.sub(r"\([^)]*\)", " ", ref)          # drop parenthetical asides
    ref = re.sub(r"pp?\.\s*[\d,\-–\s]+", " ", ref, flags=re.I)  # drop page-range notation
    parts = re.split(r"[\/,;]| - | and ", ref)
    parts = [p.strip(" .-–") for p in parts]
    parts = [p for p in parts if p and len(p) >= 2]
    # expand an alphanumeric range like 'SDK1-SDK14' or 'WB1-7' into its two endpoints —
    # a script can't safely enumerate the middle, but it can check both ends were real
    expanded = []
    for p in parts:
        m = re.match(r"^([A-Za-z]+)(\d+)-(?:([A-Za-z]+))?(\d+)$", p)
        if m:
            pre1, n1, pre2, n2 = m.groups()
            expanded.append(f"{pre1}{n1}")
            expanded.append(f"{pre2 or pre1}{n2}")
        else:
            expanded.append(p)
    return expanded


def check_exhibit_refs(rec: dict, tx_dir: str):
    """An exhibit reference that never appears in the transcript, in any of its plausible
    component tokens, is a fabrication risk worth flagging."""
    day = rec.get("day_number")
    body = load_transcript(day, tx_dir)
    out = []
    if body is None:
        return out
    for ex in rec.get("exhibits") or []:
        ref = (ex.get("ref") or "").strip()
        if not ref:
            continue
        tokens = split_ref(ref) or [ref]
        if not any(norm(t).lower() in body for t in tokens):
            out.append({"day": day, "reason": "exhibit reference not found in the transcript "
                                              "(checked whole string and split tokens)", "ref": ref})
    return out


def check_header(rec: dict):
    """The transcript prints its own day number. If the model's header_line disagrees, flag it."""
    day, hl = rec.get("day_number"), norm(rec.get("header_line") or "")
    if not hl:
        return None
    m = re.search(r"DAY\s*(\d{1,3})", hl, re.I)
    if m and int(m.group(1)) != day:
        return {"day": day, "reason": "transcript header states a different day number",
                "header_line": hl, "header_day": int(m.group(1))}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("--transcripts", default=DEFAULT_TX)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    data = json.load(open(a.infile, encoding="utf-8"))
    days = data["days"] if isinstance(data, dict) and "days" in data else data

    all_fails, ref_fails, hdr_fails = [], [], []
    kept_n = dropped_n = 0

    for rec in days:
        kept, fails = check_day(rec, a.transcripts)
        rec["quotes"] = kept
        rec["quote_verification"] = {
            "checked": len(kept) + len(fails), "kept": len(kept), "dropped": len(fails),
            "method": "exact substring match against the commission's own transcript, whitespace-normalised",
        }
        kept_n += len(kept); dropped_n += len(fails)
        all_fails += fails
        ref_fails += check_exhibit_refs(rec, a.transcripts)
        h = check_header(rec)
        if h:
            hdr_fails.append(h)
            rec.setdefault("unverified", []).append(
                f"Transcript header reads Day {h['header_day']} but this record is filed as Day {h['day']}.")

    for f in ref_fails:
        for rec in days:
            if rec.get("day_number") == f["day"]:
                rec.setdefault("unverified", []).append(
                    f"Exhibit reference {f['ref']!r} could not be found in the transcript and may be misread.")

    report = {
        "quotes_kept": kept_n, "quotes_dropped": dropped_n,
        "pass_rate": round(kept_n / max(1, kept_n + dropped_n) * 100, 1),
        "failures": all_fails, "exhibit_ref_failures": ref_fails, "header_mismatches": hdr_fails,
    }

    out = a.out or a.infile.replace(".json", ".verified.json")
    json.dump(days if not isinstance(data, dict) else {**data, "days": days},
              open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(report, open(out.replace(".json", "") + ".report.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    print(f"quotes kept {kept_n}  dropped {dropped_n}  pass rate {report['pass_rate']}%")
    if all_fails:
        print("\nDROPPED QUOTES")
        for f in all_fails:
            print(f"  day {f['day']:>3}  {f['reason']:<45} {(f.get('speaker') or '?')[:28]:<28} {f['text'][:70]!r}")
    if ref_fails:
        print("\nEXHIBIT REFS NOT IN TRANSCRIPT")
        for f in ref_fails:
            print(f"  day {f['day']:>3}  {f['ref']}")
    if hdr_fails:
        print("\nHEADER MISMATCHES")
        for f in hdr_fails:
            print(f"  filed as day {f['day']} but header says {f['header_day']}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
