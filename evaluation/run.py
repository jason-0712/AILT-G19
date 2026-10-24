"""Runs synthetic fixtures only; never pass real user queries to this runner."""
import argparse
import json
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from lostfound.config import ROOT, load_settings
from lostfound.database import read_seed, dataset_hash
from lostfound.matching import search, PROMPT_VERSION, SYSTEM_PROMPT
import hashlib

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["keyword","ai"], default="keyword")
    parser.add_argument("--output", default="evaluation/results/latest.json")
    args = parser.parse_args()
    settings = load_settings()
    if args.mode == "ai" and not settings.ai_ready:
        parser.error("AI evaluation requires provider, HTTPS base URL, model and key.")
    # Sequential pacing respects the configured process-wide request limit.
    records = read_seed()
    queries = json.loads((ROOT / "evaluation/queries.json").read_text())
    results = []
    for i, case in enumerate(queries):
        if args.mode == "ai" and i:
            time.sleep(60 / settings.requests_per_minute + 0.1)
        result = search(case["query"], records, args.mode, settings)
        hit = bool(set(case["acceptable_ids"]) & {m.id for m in result.matches})
        passed = hit if case["group"] == "known" else result.status == case["expected_status"]
        results.append({**case, "result": result.model_dump(), "passed": passed})
    groups = {}
    for case in results:
        group = groups.setdefault(case["group"], {"passed":0,"total":0})
        group["total"] += 1
        group["passed"] += int(case["passed"])
    report = {"timestamp_utc":datetime.now(timezone.utc).isoformat(), "mode":args.mode,
        "provider":settings.provider if args.mode == "ai" else None,
        "model":settings.model if args.mode == "ai" else None,
        "prompt_version":PROMPT_VERSION, "prompt_sha256":hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "dataset_sha256":dataset_hash(records), "answer_key_review":"pending second team member",
        "groups":groups, "cases":results,
        "note":"Synthetic fixture results only. Keyword overlap is not semantic matching. AI evidence accuracy still requires manual review."}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(groups,indent=2))
    print(f"Report written to {output}")

if __name__ == "__main__":
    main()
