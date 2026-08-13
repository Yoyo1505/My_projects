"""
eval.py - Evaluation script checking route accuracy, must_include, and must_not_include regexes.
Usage: python3 eval.py <golden.jsonl> <answers.jsonl>
"""

import sys
import json
import re
from collections import defaultdict


def evaluate(golden_path: str, answers_path: str):
    golden_cases = {}
    with open(golden_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                c = json.loads(line)
                golden_cases[c["id"]] = c

    answers = {}
    with open(answers_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                a = json.loads(line)
                answers[a["id"]] = a

    total = len(golden_cases)
    passed_count = 0
    route_stats = defaultdict(lambda: {"passed": 0, "total": 0})

    print(f"Evaluating {total} cases from '{answers_path}' against '{golden_path}'...\n" + "=" * 70)

    for case_id, golden in golden_cases.items():
        expected_route = golden.get("expected_route", "")
        route_stats[expected_route]["total"] += 1

        ans_obj = answers.get(case_id)
        if not ans_obj:
            print(f"[FAIL] Case {case_id}: Missing answer in '{answers_path}'")
            continue

        got_route = ans_obj.get("route", "")
        answer_text = ans_obj.get("answer", "")

        failures = []

        # 1. Check Route
        if got_route != expected_route:
            failures.append(f"Route mismatch (expected '{expected_route}', got '{got_route}')")

        # 2. Check must_include regex patterns
        for pattern in golden.get("must_include", []):
            if not re.search(pattern, answer_text, re.IGNORECASE):
                failures.append(f"Missing must_include pattern: '{pattern}'")

        # 3. Check must_not_include regex patterns
        for pattern in golden.get("must_not_include", []):
            if re.search(pattern, answer_text, re.IGNORECASE):
                failures.append(f"Matched forbidden must_not_include pattern: '{pattern}'")

        if not failures:
            passed_count += 1
            route_stats[expected_route]["passed"] += 1
            print(f"[PASS] Case {case_id:4s} | Route: {got_route:8s}")
        else:
            reasons = "; ".join(failures)
            print(f"[FAIL] Case {case_id:4s} | Route: expected='{expected_route}', got='{got_route}'\n       Failure Reason(s): {reasons}")

    print("=" * 70)
    percentage = (passed_count / total * 100) if total > 0 else 0.0
    print(f"SUMMARY: {passed_count}/{total} passed ({percentage:.1f}%)\n")
    print("Breakdown by expected route:")
    for route in ["policy", "tool", "both", "escalate"]:
        r_passed = route_stats[route]["passed"]
        r_total = route_stats[route]["total"]
        pct = (r_passed / r_total * 100) if r_total > 0 else 0.0
        print(f"  {route:10s}: {r_passed}/{r_total} passed ({pct:.1f}%)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 eval.py <golden.jsonl> <answers.jsonl>")
        sys.exit(1)
    evaluate(sys.argv[1], sys.argv[2])
