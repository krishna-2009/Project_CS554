#!/usr/bin/env python3
"""Reproduce finite experiments, cross-check SC/TSO, and generate report tables."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / "results" / name).read_text())


def tex(text):
    return str(text).replace("_", r"\_")


def tables_and_validate():
    herd, cds, ref = (read(x) for x in ("herd_summary.json", "cds_summary.json", "reference_summary.json"))
    if not herd["passed"] or len(herd["runs"]) != 46 or len(cds["tests"]) != 9:
        raise RuntimeError("Incomplete experiment matrix; no report generated")
    for rel, digest in herd["input_sha256"].items():
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Stale herd result for changed input {rel}; rerun experiments")
    for r in cds["tests"]:
        source = ROOT / "cdschecker_tests" / (r["test"] + ".cc")
        if hashlib.sha256(source.read_bytes()).hexdigest() != r["source_sha256"]:
            raise RuntimeError(f"Stale CDSChecker result for {source.name}")
        for rel, digest in r["source_files_sha256"].items():
            if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != digest:
                raise RuntimeError(f"Stale CDSChecker result for changed input {rel}")
        if r["status"] != "completed" or r["total"] <= 0:
            raise RuntimeError(f"No completed CDSChecker exploration for {r['test']}")
        expected_bug = r["test"] in {"peterson_entry_relaxed", "peterson_entry_acqrel",
                                     "peterson_race_relaxed", "peterson_race_acqrel"}
        if bool(r["buggy"]) != expected_bug:
            raise RuntimeError(f"Unexpected CDSChecker outcome for {r['test']}; inspect raw log")
    comparisons = []
    for r in ref["results"]:
        kind = "peterson" if r["test"].startswith("peterson") else "sb"
        fenced = r["test"].endswith("_mfence")
        test = ("peterson_mfence" if fenced else "peterson_unfenced") if kind == "peterson" else ("sb_mfence" if fenced else "sb")
        h = next(x for x in herd["runs"] if x["model"] == r["model"].lower() and x["test"] == test)
        # Compare complete sets of observed register values, not graph witness
        # counts. Distinct rf/co choices can yield identical register values.
        content = (ROOT / h["raw_log"]).read_text()
        observed = set()
        for line in content.splitlines():
            if not line.startswith("0:EAX="):
                continue
            regs = dict(re.findall(r"([01]:E[AB]X)=(\d+)", line))
            if kind == "peterson":
                observed.add(((int(regs["0:EAX"]), int(regs["0:EBX"])),
                              (int(regs["1:EAX"]), int(regs["1:EBX"]))))
            else:
                observed.add(((int(regs["0:EAX"]), -1), (int(regs["1:EAX"]), -1)))
        reference_values = {tuple(tuple(thread) for thread in value) for value in r["final_register_values"]}
        if observed != reference_values or h["allowed"] != r["violation_reachable"]:
            raise RuntimeError(f"SC/TSO differential check failed: {r['model']} {test}")
        comparisons.append({"model": r["model"], "test": test, "equal_final_register_sets": True,
                            "register_projections": len(observed)})
    (ROOT / "results/crosscheck.json").write_text(json.dumps({"passed": True,
        "count_unit": "distinct observed register projections", "comparisons": comparisons}, indent=2) + "\n")
    lines = ["% Generated from completed experiments; do not edit counts by hand.",
             r"\begin{tabular}{llrr}", r"\toprule Test & Model & Positive & Negative \\", r"\midrule"]
    for r in herd["runs"]:
        lines.append(f"{tex(r['test'])} & {r['model'].upper()} & {r['positive']} & {r['negative']} " + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}", "", r"\begin{tabular}{lrrrr}",
              r"\toprule CDSChecker harness & Complete & Buggy & Infeasible & Total \\", r"\midrule"]
    for r in cds["tests"]:
        lines.append(f"{tex(r['test'])} & {r['complete_bug_free']} & {r['buggy']} & {r['infeasible']} & {r['total']} " + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (ROOT / "results/generated_tables.tex").write_text("\n".join(lines) + "\n")
    selected = [("Peterson: plain stores", "peterson_unfenced"),
                ("Peterson: MFENCE", "peterson_mfence"),
                ("Peterson: dummy RMW", "peterson_rmw_fence"),
                ("Peterson: turn RMW", "peterson_turn_rmw"),
                ("Dekker doorway", "dekker_entry"), ("2+2W calibration", "twop2w")]
    small = [r"\begin{tabular}{lrrrr}", r"\toprule Entry test / calibration & SC & TSO & RA & SRA \\", r"\midrule"]
    for label, test in selected:
        values = []
        for model in ("sc", "tso", "ra", "sra"):
            row = next((r for r in herd["runs"] if r["model"] == model and r["test"] == test), None)
            values.append(str(row["positive"]) if row else "--")
        small.append(label + " & " + " & ".join(values) + r" \\")
    small += [r"\bottomrule", r"\end{tabular}"]
    (ROOT / "report/checkin_herd_table.tex").write_text("\n".join(small) + "\n")
    labels = {"peterson_entry_relaxed": "Peterson entry: relaxed",
              "peterson_entry_acqrel": "Peterson entry: release/acquire",
              "peterson_entry_seqcst": "Peterson entry: seq\\_cst",
              "peterson_race_relaxed": "Peterson payload: relaxed",
              "peterson_race_acqrel": "Peterson payload: release/acquire",
              "peterson_race_seqcst": "Peterson payload: seq\\_cst",
              "spinlock_acqrel": "TAS try-lock: acquire/release",
              "ticket_acqrel": "Ticket lock: acquire/release",
              "spsc_queue_ra": "SPSC one-item publication"}
    small = [r"\begin{tabular}{lrr}", r"\toprule CDSChecker harness & Total & Buggy \\", r"\midrule"]
    for r in cds["tests"]:
        small.append(f"{labels[r['test']]} & {r['total']} & {r['buggy']} " + r"\\")
    small += [r"\bottomrule", r"\end{tabular}"]
    (ROOT / "report/checkin_cds_table.tex").write_text("\n".join(small) + "\n")
    print("Validated 46 herd runs, 9 CDSChecker harnesses, and 8 independent SC/TSO register-set comparisons.")


def build_pdf():
    report = ROOT / "report"
    for _ in range(2):
        result = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "checkin.tex"],
                                cwd=report, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (ROOT / "results/checkin_build.log").write_text(result.stdout)
        if result.returncode:
            raise RuntimeError("Check-in PDF build failed; see results/checkin_build.log")
    log = (report / "checkin.log").read_text()
    if any(marker in log for marker in ("Overfull", "undefined references", "LaTeX Warning: Reference")):
        raise RuntimeError("Check-in PDF needs layout/reference review; see report/checkin.log")
    info = subprocess.check_output(["pdfinfo", str(report / "checkin.pdf")], text=True)
    pages = re.search(r"^Pages:\s+(\d+)", info, re.M)
    if not pages or int(pages[1]) != 2:
        raise RuntimeError("The check-in must fit two pages; review report/checkin.pdf")
    print("Built report/checkin.pdf (2 pages).")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tables-only", action="store_true", help="validate saved summaries and regenerate tables without rerunning tools")
    ap.add_argument("--pdf", action="store_true", help="also compile the check-in PDF")
    ap.add_argument("--graphs", action="store_true", help="regenerate selected herd DOT witnesses")
    args = ap.parse_args()
    if not args.tables_only:
        for script, extra in (("reference_checker.py", []), ("run_herd.py", ["--graphs"] if args.graphs else []), ("run_cds.py", [])):
            subprocess.run([sys.executable, str(ROOT / "scripts" / script)] + extra, cwd=ROOT, check=True)
    tables_and_validate()
    if args.pdf:
        build_pdf()


if __name__ == "__main__":
    main()
