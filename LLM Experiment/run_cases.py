"""
run_cases.py - Standard evaluation script contract for SplitWave Support Agent.
Usage: python3 run_cases.py <cases.jsonl> <answers.jsonl>
"""

import sys
import json
from graph import run as answer


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 run_cases.py <cases.jsonl> <answers.jsonl>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    answers = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            case_id = case.get("id")
            question = case.get("question", "")
            user_id = case.get("user_id", "")

            res = answer(question, user_id)
            answers.append({
                "id": case_id,
                "route": res.get("route", "policy"),
                "answer": res.get("answer", "")
            })

    with open(output_path, "w", encoding="utf-8") as f:
        for ans in answers:
            f.write(json.dumps(ans) + "\n")

    print(f"Successfully processed {len(answers)} cases from '{input_path}' -> '{output_path}'")


if __name__ == "__main__":
    main()
