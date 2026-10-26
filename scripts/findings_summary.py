#!/usr/bin/env python3
"""Validate and total the findings.csv files that back the numbers quoted in the docs.

Usage: scripts/findings_summary.py [--check] [file ...]
Default files: every examples/*/findings.csv and evals/*/findings.csv.
--check prints nothing but problems (exit 1 if any); otherwise prints totals.
"""
import collections, csv, glob, os, sys

COLUMNS = ["id", "stage", "severity", "caught_by", "found_in_round", "summary", "category", "fix_status", "solo_first_pass_had_it"]
ENUMS = {
    "severity": {"BLOCKER", "MAJOR", "MINOR", "NIT"},
    "category": {"correctness", "security", "concurrency", "tests", "design", "accessibility", "docs", "other"},
    "fix_status": {"fixed", "accepted", "open", "unknown"},
    "solo_first_pass_had_it": {"yes", "no", "partial", "n/a", "untested"},
}


def load(path):
    problems, rows = [], []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            return ["%s: header is %s, expected %s" % (path, reader.fieldnames, COLUMNS)], []
        seen = set()
        for n, r in enumerate(reader, 2):
            if None in r or None in r.values():
                problems.append("%s:%d: wrong number of fields" % (path, n)); continue
            if r["id"] in seen: problems.append("%s:%d: duplicate id %s" % (path, n, r["id"]))
            seen.add(r["id"])
            for k, ok in ENUMS.items():
                if r[k] not in ok: problems.append("%s:%d: %s=%r not in %s" % (path, n, k, r[k], sorted(ok)))
            if r["found_in_round"] and not r["found_in_round"].isdigit():
                problems.append("%s:%d: found_in_round must be blank or an integer" % (path, n))
            if not r["summary"].strip(): problems.append("%s:%d: empty summary" % (path, n))
            rows.append(r)
    return problems, rows


def main(argv):
    check = "--check" in argv
    files = [a for a in argv if not a.startswith("--")] or sorted(glob.glob("examples/*/findings.csv") + glob.glob("evals/*/findings.csv"))
    bad = 0
    for p in files:
        problems, rows = load(p)
        for m in problems: print("FAIL:", m, file=sys.stderr)
        bad += len(problems)
        if check or problems: continue
        sev = collections.Counter(r["severity"] for r in rows)
        who = collections.Counter(r["caught_by"] for r in rows)
        solo = collections.Counter(r["solo_first_pass_had_it"] for r in rows)
        print("%s: %d findings; %s; by role: %s; solo first pass had it: %s" % (
            p, len(rows), ", ".join("%d %s" % (sev[s], s) for s in ("BLOCKER", "MAJOR", "MINOR", "NIT") if sev[s]),
            ", ".join("%s %d" % kv for kv in sorted(who.items())), ", ".join("%s %d" % kv for kv in sorted(solo.items()))))
    return 1 if bad else 0


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    sys.exit(main(sys.argv[1:]))
