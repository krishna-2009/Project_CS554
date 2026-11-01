#!/usr/bin/env python3
"""Independent finite SC/TSO operational cross-check for the entry litmus tests.

This deliberately small checker is not herd7, a C11 checker, or a proof of an
unbounded lock. TSO uses one FIFO store buffer per thread and reads forward the
newest local buffered write to the same location. MFENCE waits for an empty
buffer. Every program is a finite, straight-line entry fragment without unlock.
Counts are distinct final register projections, never schedule counts.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def programs(kind: str, fenced: bool):
    if kind == "peterson":
        p = [(("W", i, 1), ("W", 2, 1-i), ("R", 1-i, 0), ("R", 2, 1))
             for i in range(2)]
        if fenced:
            p = [q[:2] + (("F",),) + q[2:] for q in p]
        return tuple(p), ("flag0", "flag1", "turn")
    p = [(("W", i, 1), ("R", 1-i, 0)) for i in range(2)]
    if fenced:
        p = [q[:1] + (("F",),) + q[1:] for q in p]
    return tuple(p), ("x", "y")


def explore(kind: str, fenced: bool, model: str):
    prog, names = programs(kind, fenced)
    # pc, memory, registers (two slots per thread), per-thread FIFO buffers.
    initial = ((0, 0), (0,) * len(names), ((-1, -1), (-1, -1)), ((), ()))
    parent = {initial: None}
    pending = deque([initial])
    finals = {}
    edges = 0

    def successors(s):
        pcs, mem, regs, bufs = s
        for tid in range(2):
            if (pcs[tid] < len(prog[tid])
                    and not (prog[tid][pcs[tid]][0] == "F" and bufs[tid])):
                op = prog[tid][pcs[tid]]
                new_pc, new_mem, new_regs, new_bufs = list(pcs), list(mem), list(regs), list(bufs)
                new_pc[tid] += 1
                if op[0] == "W":
                    _, loc, val = op
                    if model == "TSO":
                        new_bufs[tid] = bufs[tid] + ((loc, val),)
                    else:
                        new_mem[loc] = val
                    action = f"T{tid}: W {names[loc]}={val}" + (" (buffered)" if model == "TSO" else "")
                elif op[0] == "R":
                    _, loc, reg = op
                    val = next((v for l, v in reversed(bufs[tid]) if l == loc), mem[loc])
                    rr = list(regs[tid])
                    rr[reg] = val
                    new_regs[tid] = tuple(rr)
                    action = f"T{tid}: R {names[loc]}={val} -> r{reg}"
                else:
                    action = f"T{tid}: MFENCE"
                yield (tuple(new_pc), tuple(new_mem), tuple(new_regs), tuple(new_bufs)), action
            if model == "TSO" and bufs[tid]:
                loc, val = bufs[tid][0]
                new_mem, new_bufs = list(mem), list(bufs)
                new_mem[loc] = val
                new_bufs[tid] = bufs[tid][1:]
                yield (pcs, tuple(new_mem), regs, tuple(new_bufs)), f"T{tid}: flush {names[loc]}={val}"

    while pending:
        s = pending.popleft()
        if all(s[0][t] == len(prog[t]) for t in range(2)) and not any(s[3]):
            finals.setdefault(s[2], s)
        for nxt, action in successors(s):
            edges += 1
            if nxt not in parent:
                parent[nxt] = (s, action)
                pending.append(nxt)

    def bad(regs):
        if kind == "peterson":
            return ((regs[0][0] == 0 or regs[0][1] == 0)
                    and (regs[1][0] == 0 or regs[1][1] == 1))
        return regs[0][0] == 0 and regs[1][0] == 0

    positive = [r for r in finals if bad(r)]
    trace = []
    if positive:
        state = finals[positive[0]]
        while parent[state] is not None:
            state, action = parent[state]
            trace.append(action)
        trace.reverse()
    return {
        "test": kind + ("_mfence" if fenced else "_unfenced"), "model": model,
        "scope": "two threads; one finite entry fragment each; no unlock; zero initialization",
        "property": "both entry predicates true" if kind == "peterson" else "both reads zero",
        "reachable_states": len(parent), "transitions": edges,
        "final_register_projections": len(finals),
        "positive_register_projections": len(positive),
        "both_zero_register_projections": sum(r[0][0] == r[1][0] == 0 for r in finals),
        "violation_reachable": bool(positive),
        "final_register_values": sorted(finals),
        "positive_register_values": positive,
        "first_counterexample_schedule": trace,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/reference_summary.json")
    args = parser.parse_args()
    rows = [explore(kind, fenced, model)
            for kind in ("sb", "peterson")
            for fenced in (False, True) for model in ("SC", "TSO")]
    # Independent expected outcomes for the classic SB calibration and Peterson
    # entry fragment. A disagreement fails the run instead of producing a table.
    for r in rows:
        expected = r["model"] == "TSO" and r["test"].endswith("_unfenced")
        if not r["final_register_projections"] or r["violation_reachable"] != expected:
            raise SystemExit(f"Unexpected calibration outcome: {r}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"checker": "finite operational reference",
        "count_unit": "distinct final register projections", "results": rows}, indent=2) + "\n")
    for r in rows:
        print(f'{r["test"]:22} {r["model"]:3} '
              f'bad projections={r["positive_register_projections"]}/{r["final_register_projections"]}; '
              f'states={r["reachable_states"]}')


if __name__ == "__main__":
    main()
