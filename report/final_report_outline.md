# Final report outline

1. **Motivation:** low-level lock implementation and the SC-DRF abstraction.
2. **Models:** SC, TSO, RA, SRA, update atomicity, and the C11/C++11 checker.
3. **Flag-based protocols:** Peterson admission conditions, Dekker coverage,
   and weak-memory counterexamples.
4. **Repairs:** hardware MFENCE, shared dummy exchanges, turn exchanges,
   and language-level seq_cst operations.
5. **RMW synchronization:** TAS and ticket-lock safety, protected-data
   visibility, and SPSC publication.
6. **Experiments:** test bounds, witness counts, register projections,
   checker statistics, and reproducibility.
7. **Limitations and conclusion:** achieved scope, remaining cases, and the
   distinction between finite checking and a general correctness proof.

Candidate figures include the TSO store-buffering execution, the RA/SRA
Peterson dummy-exchange witness, and the 2+2W distinction. Results tables
are generated from the JSON summaries in `results/`.
