# CS 554: Lock Algorithms Across Memory Models

Krishna Riteshkumar Patel · UIN 670178497 · Fall 2026

This project compares bounded lock-entry and synchronization protocols under
SC, x86-TSO, RA, SRA, and the C11/C++11 model implemented by CDSChecker. The
experiments examine weak-memory violations, fence placement, atomic exchanges,
and protected-data visibility.

## Check-in report

- `report/checkin.pdf`: two-page progress report.
- `report/checkin.tex`: editable LaTeX source.
- `submission/CS554_CheckIn_Project.zip`: report, code, models, and results.
- `docs/submitted_proposal.pdf`: original project proposal.

## Build and reproduce

Requirements: Linux, Python 3, GNU Make, g++, and LaTeX with the packages used
in `report/checkin.tex`. PDF checks also require `pdfinfo` from Poppler.

```bash
make reproduce
```

This runs 46 herd7 model/test pairs, nine CDSChecker harnesses, and eight
SC/TSO comparisons with an independent finite operational checker. It also
generates result tables and builds the report. The runner rejects incomplete
output, crashes, timeouts, stale input hashes, and unexpected outcomes.

Individual commands:

```bash
python3 scripts/run_herd.py --graphs
python3 scripts/run_cds.py
python3 scripts/reference_checker.py
make checkin
make package
```

`make checkin` validates saved results and rebuilds the PDF. `make package`
creates `submission/CS554_CheckIn_Project.zip` and updates `MANIFEST.sha256`.
Local binaries, LaTeX auxiliary files, and submission archives are excluded
from Git.

The bundled herd7 7.58 executable targets Linux x86-64 with glibc 2.42 or
later. Other systems can rebuild it using `scripts/build_herd.sh` or supply a
compatible executable through `HERD7`. CDSChecker is built from the included
source. Tool versions and compatibility details are in `docs/HERD.md` and
`docs/CDSCHECKER.md`.

## Models and experiments

SC and TSO use the unmodified upstream herdtools7 models. The custom RA/SRA
models follow the all-acquire/all-release fragment of Lahav et al. RA/SRA
runs use x86-shaped parser syntax as an abstract event language: reads are
acquire, writes are release, and exchanges are acquire-release. Native
MFENCE tests are evaluated under SC/TSO only. CDSChecker provides a separate
historical C11/C++11 interpretation.

The litmus suite covers store buffering, message passing, 2+2W, Peterson
entry variants, and Dekker's initial flag doorway. The language harnesses
check Peterson admission and payload races, a TAS try-lock, a bounded ticket
lock, and one-item SPSC publication.

## Results

| Peterson entry variant | SC positive | TSO positive | RA positive | SRA positive |
|---|---:|---:|---:|---:|
| Plain stores | 0 | 6 | 6 | 6 |
| MFENCE after turn store | 0 | 0 | — | — |
| Shared dummy exchange after turn store | 0 | 0 | 2 | 2 |
| Turn store replaced by exchange | 0 | 0 | 0 | 0 |

Positive counts are herd execution witnesses satisfying the bad-outcome
condition. They are not probabilities or scheduler-path counts. The Peterson
condition checks both full admission predicates. The shared dummy exchange
blocks the both-zero flag outcome but leaves two other admission violations
under RA/SRA. The turn-exchange variant has no violating witnesses in this
fragment.

CDSChecker reports five admission assertion violations out of 12 candidates
for each weak Peterson variant, and none out of eight for the all-seq_cst
variant. The TAS, ticket, and one-item publication harnesses report no bugs
within their bounds. Full counters, including infeasible and redundant
candidates, are in `results/cds_summary.json`. The independent SC/TSO checker
matches all observed register sets in eight comparisons.

## Scope and remaining work

Litmus tests are two-thread, one-pass fragments without unlocks. Peterson
reads both guard variables unconditionally. The Dekker test omits turn
arbitration and backoff. Language harness bounds are documented in
`docs/CDSCHECKER.md`.

These experiments establish bounded safety results, not fairness, termination,
starvation freedom, or unbounded correctness. Remaining work includes full
Dekker, repeated acquisitions, the language-level turn-exchange repair,
simplified RCU, and the final report. SPSC slot reuse is a stretch goal.

## Repository layout

| Directory | Contents |
|---|---|
| `models/` | SC/TSO source copies, custom RA/SRA encodings, provenance |
| `litmus/` | Finite entry and calibration tests |
| `cdschecker_tests/` | C11/C++11 harnesses and shared Peterson code |
| `scripts/` | Experiment runners, tool build, patch, and packaging |
| `results/` | JSON summaries, raw logs, tables, and counterexample DOT graphs |
| `report/` | Check-in PDF, LaTeX source, and final-report outline |
| `docs/` | Formal definitions, design notes, references, and tool instructions |
| `submission/` | Submission archive and packaging notes |
| `vendor/` | Pinned tools with upstream licenses and revision metadata |

Technical details are in `docs/formal_scope.md` and `docs/technical_audit.md`.
Vendored code retains its original licenses.
