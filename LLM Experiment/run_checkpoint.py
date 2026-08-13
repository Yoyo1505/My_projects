"""
run_checkpoint.py - Foreground-safe chunked runner with checkpoint/resume.
Persists each result immediately; skips IDs already present in the output file.
Usage: python run_checkpoint.py <cases.jsonl> <answers.jsonl> <chunk_size>
"""
import sys
import json
import os
from graph import run as answer


def load_done_ids(path):
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    done.add(json.loads(line)["id"])
                except Exception:
                    pass
    return done


def main():
    cases_path, out_path, chunk_size = sys.argv[1], sys.argv[2], int(sys.argv[3])
    done = load_done_ids(out_path)

    pending = []
    with open(cases_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            if c["id"] not in done:
                pending.append(c)

    total_cases = sum(1 for _ in open(cases_path, encoding="utf-8") if _.strip())

    if not pending:
        print(f"ALL_DONE done={len(done)} total={total_cases}")
        return

    todo = pending[:chunk_size]
    with open(out_path, "a", encoding="utf-8") as out:
        for c in todo:
            res = answer(c["question"], c["user_id"])
            rec = {"id": c["id"], "route": res.get("route", "policy"), "answer": res.get("answer", "")}
            out.write(json.dumps(rec) + "\n")
            out.flush()
            print(f"CHECKPOINT {c['id']} route={rec['route']}")

    remaining = len(pending) - len(todo)
    print(f"CHUNK_DONE processed={len(todo)} remaining={remaining} done_total={len(done)+len(todo)} of {total_cases}")


if __name__ == "__main__":
    main()
