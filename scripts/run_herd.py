#!/usr/bin/env python3
"""Run the bounded project suite with pinned SC/TSO and audited RA/SRA cats."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TESTS = ["sb", "sb_mfence", "mp", "twop2w", "dekker_entry",
         "dekker_entry_mfence", "peterson_unfenced", "peterson_both_zero",
         "peterson_mfence", "sb_rmw_fence", "peterson_rmw_fence",
         "peterson_rmw_fence_both_zero", "peterson_turn_rmw"]
MFENCE_TESTS = {"sb_mfence", "dekker_entry_mfence", "peterson_mfence"}
MODELS = ["sc", "tso", "ra", "sra"]

def expected(model, test):
    if test in MFENCE_TESTS or test in {"mp", "sb_rmw_fence", "peterson_turn_rmw", "peterson_rmw_fence_both_zero"}:
        return False
    if test == "twop2w":
        return model == "ra"
    if test == "peterson_rmw_fence":
        return model in {"ra", "sra"}
    return model != "sc"

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graphs", action="store_true", help="also regenerate selected counterexample DOT graphs")
    args = ap.parse_args()
    installed = os.environ.get("HERD7") or shutil.which("herd7")
    fallback = ROOT / "vendor/herdtools7/bin/herd7"
    herd = str(Path(installed).resolve()) if installed else str(fallback)
    if not Path(herd).is_file():
        sys.exit("herd7 not found: install herdtools7 7.58 or set HERD7 to its executable")
    lib = ROOT / "vendor/herdtools7/herd/libdir"
    if not lib.is_dir():
        sys.exit("Missing pinned upstream herd/libdir. See README for source setup.")
    version = subprocess.check_output([herd, "-version"], text=True).strip()
    raw = ROOT / "results/herd_raw"
    raw.mkdir(parents=True, exist_ok=True)
    rows = []
    for model in MODELS:
        for test in TESTS:
            if model in {"ra", "sra"} and test in MFENCE_TESTS:
                continue
            relative = ["-I", "vendor/herdtools7/herd/libdir", "-I", "models", "-model",
                        f"models/{model}.cat", f"litmus/{test}.litmus"]
            result = subprocess.run([herd] + relative, cwd=ROOT, capture_output=True, text=True, timeout=120)
            log = raw / f"{model}__{test}.log"
            log.write_text(result.stdout + result.stderr)
            counts = re.search(r"Positive:\s+(\d+)\s+Negative:\s+(\d+)", result.stdout)
            states = re.search(r"^States\s+(\d+)", result.stdout, re.M)
            obs = re.search(r"^Observation\s+\S+\s+(Never|Sometimes|Always)\s+(\d+)\s+(\d+)", result.stdout, re.M)
            # herd can report some parsing failures with exit 0: require all markers.
            if result.returncode or not counts or not states or not obs or "Fatal" in result.stderr:
                raise RuntimeError(f"Failed {model}/{test}; inspect {log}")
            positive, negative = map(int, counts.groups())
            allowed = positive > 0
            row = dict(model=model, test=test, positive=positive, negative=negative,
                       allowed=allowed, outcome="allowed" if allowed else "forbidden",
                       observed=obs[1], states=int(states[1]), count_unit="herd_execution_witnesses",
                       command=["herd7"] + relative, raw_log=str(log.relative_to(ROOT)),
                       exit_code=result.returncode, expected_allowed=expected(model, test),
                       expectation_passed=allowed == expected(model, test))
            rows.append(row)
            print(f"{model:3} {test:31} {row['outcome']:9} Positive={positive} Negative={negative}")
    files = list((ROOT / "models").glob("*.cat")) + list((ROOT / "litmus").glob("*.litmus"))
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    summary = dict(tool="herd7", version=version,
                   upstream_commit="1ca343e16a2038e406d1ac674e7e3a1b722b36c7",
                   scope="Fixed one-pass, two-thread fragments; no reset/unlock; no liveness proof. RA/SRA use abstract acquire/release interpretation, not x86 hardware semantics.",
                   count_note="Positive/Negative count allowed execution witnesses; states are distinct projections onto observed locations/registers and depend on each test condition. Neither is a scheduler-path count.",
                   passed=all(r["expectation_passed"] for r in rows), input_sha256=hashes, runs=rows)
    (ROOT / "results/herd_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    if not summary["passed"]:
        sys.exit("One or more calibrated expectations failed; do not silently use these results.")
    if args.graphs:
        for model, test in [("tso", "peterson_unfenced"), ("ra", "peterson_rmw_fence"), ("ra", "twop2w")]:
            graphdir = ROOT / "results/herd_graphs" / model
            graphdir.mkdir(parents=True, exist_ok=True)
            cmd = [herd, "-I", str(lib), "-I", "models", "-model", f"models/{model}.cat",
                   "-show", "prop", "-o", str(graphdir), f"litmus/{test}.litmus"]
            subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True, timeout=120)
    print(f"Completed {len(rows)} runs; calibrated expectations passed.")

if __name__ == "__main__":
    main()
