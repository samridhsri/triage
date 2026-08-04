#!/usr/bin/env python3
"""
Run split_intents() against the golden dataset and report pass/fail.

Usage:
    python evaluation/eval.py
    python evaluation/eval.py --real-only   # skip synthetic cases
    python evaluation/eval.py --tag task    # filter by tag

Must be run from the project root (so splitter_prompt.txt is found).
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

from llm import split_intents

CASES_PATH = Path(__file__).parent / "cases.json"


def _match_intent(spec, candidates):
    """Return first candidate satisfying spec (mutates nothing), or None."""
    if "type_options" in spec:
        allowed = set(spec["type_options"])
    elif "type" in spec:
        allowed = {spec["type"]}
    else:
        allowed = None  # any type

    for c in candidates:
        if allowed is not None and c.get("type") not in allowed:
            continue
        title = (c.get("title") or "").lower()
        if any(kw.lower() not in title for kw in spec.get("title_contains", [])):
            continue
        if not all(c.get(k) == v for k, v in spec.get("fields", {}).items()):
            continue
        return c
    return None


def score_case(case, actual):
    """Return (passed: bool, failures: list[str])."""
    expected = case["expected"]
    failures = []

    if len(actual) != len(expected):
        failures.append(f"count: got {len(actual)}, expected {len(expected)}")

    remaining = list(actual)
    for spec in expected:
        match = _match_intent(spec, remaining)
        if match is None:
            if "type_options" in spec:
                type_desc = "/".join(spec["type_options"])
            else:
                type_desc = spec.get("type", "?")
            parts = [f"type={type_desc}"]
            if "title_contains" in spec:
                parts.append(f"title∋{spec['title_contains']}")
            if "fields" in spec:
                parts.append(f"fields={spec['fields']}")
            failures.append("no match for: " + ", ".join(parts))
        else:
            remaining.remove(match)

    return not failures, failures


def run(real_only=False, tag_filter=None):
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = data["cases"]

    if real_only:
        cases = [c for c in cases if c.get("source") == "real"]
    if tag_filter:
        cases = [c for c in cases if tag_filter in c.get("tags", [])]

    if not cases:
        print("No cases matched filters.")
        return

    passed_total = 0
    source_stats = defaultdict(lambda: [0, 0])
    tag_stats = defaultdict(lambda: [0, 0])

    for case in cases:
        actual = split_intents(case["input"])
        ok, failures = score_case(case, actual)

        label = "PASS" if ok else "FAIL"
        print(f"{label}  [{case['id']}]  {case['input'][:70]!r}")
        for f in failures:
            print(f"       → {f}")
        if not ok:
            for a in actual:
                print(f"       got: {a.get('type')} {a.get('title')!r}")

        if ok:
            passed_total += 1

        src = case.get("source", "synthetic")
        source_stats[src][1] += 1
        if ok:
            source_stats[src][0] += 1

        for tag in case.get("tags", []):
            tag_stats[tag][1] += 1
            if ok:
                tag_stats[tag][0] += 1

    total = len(cases)
    pct = 100 * passed_total / total if total else 0
    print(f"\nResults: {passed_total}/{total} passed ({pct:.1f}%)")

    print("\nBy source:")
    for src in sorted(source_stats):
        p, n = source_stats[src]
        pct_s = 100 * p / n if n else 0
        print(f"  {src:<12} {p}/{n} ({pct_s:.0f}%)")

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("\nBy tag:")
    for tag in sorted(tag_stats):
        p, n = tag_stats[tag]
        try:
            bar = "█" * p + "░" * (n - p)
            print(f"  {tag:<16} {p:>2}/{n:<2}  {bar}")
        except UnicodeEncodeError:
            bar = "#" * p + "-" * (n - p)
            print(f"  {tag:<16} {p:>2}/{n:<2}  {bar}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-only", action="store_true", help="Only run real (non-synthetic) cases")
    parser.add_argument("--tag", help="Only run cases with this tag")
    args = parser.parse_args()
    run(real_only=args.real_only, tag_filter=args.tag)
