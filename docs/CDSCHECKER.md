# C11/C++11 model-checking harnesses

The project uses [CDSChecker's public source](https://github.com/computersforpeace/model-checker) at revision `5c4efe5cd8bdfe1e85138396109876a121ca61d1`. The upstream [README](../vendor/cdschecker/README.md) documents the interface and result categories. The tool implements a historical C11/C++11 memory-model interpretation; these runs do not establish conformance to the current ISO C++ standard or equivalence with the course's formal RA/SRA models.

## Reproduce

From the project root, on Linux with Python 3, GCC/G++, and Make:

```bash
python3 scripts/run_cds.py
```

This builds the vendored checker and each harness, sets `LD_LIBRARY_PATH` in the subprocess environment, runs without optional fairness or liveness flags, and saves raw logs plus `results/cds_summary.json`. To run one harness:

```bash
python3 scripts/run_cds.py --test peterson_entry_acqrel
```

The complete checker options and defaults are retained in `results/cds/checker-help.log`. The runner imposes a 120-second wall-clock limit per test, configurable by `--timeout`; a timeout is an error, never a passing verification. These harnesses terminate through explicit code bounds, without fairness assumptions. `--test` replaces the summary with that selected run; use the default command to regenerate the full table.

## Compatibility work

- The checker is built explicitly as C++11 because modern GCC defaults reject its legacy dynamic exception specifications. All checker translation units are built at `-O0` for this dataset.
- The sole source modification changes `BOOTSTRAPBYTES` from 4 KiB to 1 MiB. Modern runtime initialization exhausted the original bootstrap allocator before model checking began. The exact patch is in `scripts/patches/cdschecker-bootstrap.patch`, also copied into the result directory. No memory-model algorithm was changed.
- Test executables use `-no-pie` and eager symbol binding (`-Wl,-z,now`). They compile against the checker's own `stdatomic.h`, `threads.h`, and instrumentation headers and link to `libmodel.so`.
- Harnesses do not print from model-controlled threads. The upstream `userprog.c` smoke test's `printf` caused a replay-location assertion in this environment after its first trace: libc's buffering allocation changed replay heap layout. The actual no-print harnesses finish with the checker's completion marker. A checker-internal assertion is an error, not an algorithm counterexample.

The source license is GPL v2; its `LICENSE` and attribution remain in `vendor/cdschecker/`.

## Properties and bounds

| Harness | Finite program | Property |
|---|---|---|
| `peterson_entry_{relaxed,acqrel,seqcst}` | Two threads, one entry guard observation each, no unlock | Main joins both threads and asserts they did not both decide to enter. |
| `peterson_race_{relaxed,acqrel,seqcst}` | Two threads, one acquisition attempt each, at most two guard observations; failed attempt withdraws its flag | `store_32` instruments a non-atomic payload write in the critical section. |
| `spinlock_acqrel` | Two threads, one test-and-set try-lock each | Instrumented payload increment; final payload equals the number of successful acquisitions. |
| `ticket_acqrel` | Two threads, one ticket each, at most three serving polls | Instrumented payload increment; final payload equals successful acquisitions. An unserved ticket remains unserved at the bound. |
| `spsc_queue_ra` | One producer, one consumer, one slot, one item, one consumer observation, no slot reuse | When an acquire sees `ready=1`, the instrumented slot read must yield 42. |

The doorway harness records each entry decision in a separate ordinary variable and reads it only after joining both threads. It adds no cross-thread monitor RMW that could strengthen ordering and hide the bug. It is a finite doorway check, not the complete lock implementation. The race probes contain bounded acquisition/release code and are separate from this assertion check.

For `acqrel`, stores use `memory_order_release` and loads use `memory_order_acquire`; `memory_order_acq_rel` would be invalid on these plain operations. The `seqcst` variants use sequentially consistent loads and stores throughout. They do not claim to test an SC-fence-only repair.

The RMW lock tests check both publication and payload safety in whichever order acquisitions occur. They do not require a reader that acquires first to see a later writer's value. The ticket harness and one-shot TAS harness do not prove starvation freedom. The SPSC test is the single-slot publication core, not a verified reusable ring buffer.

## Recorded results

| Harness | Complete, bug-free | Buggy | Infeasible | Total |
|---|---:|---:|---:|---:|
| Peterson entry relaxed | 7 | 5 | 0 | 12 |
| Peterson entry release/acquire | 7 | 5 | 0 | 12 |
| Peterson entry seq_cst | 8 | 0 | 0 | 8 |
| Peterson payload relaxed | 17 | 39 | 48 | 104 |
| Peterson payload release/acquire | 37 | 7 | 0 | 44 |
| Peterson payload seq_cst | 34 | 0 | 0 | 34 |
| TAS try-lock acquire/release | 6 | 0 | 0 | 6 |
| Ticket acquire/release | 16 | 0 | 0 | 16 |
| SPSC publication acquire/release | 2 | 0 | 0 | 2 |

Redundant executions were zero in every run. Total is the sum of complete bug-free, buggy, redundant, and infeasible candidates. It is not a count of feasible witnesses comparable to herd7's witness count. The raw logs show assertion failures for the two weak doorway variants and race reports for the two weak payload variants. A race warning reports unordered conflicting memory accesses; by itself, it does not demonstrate simultaneous critical-section occupancy. Per-byte race messages may repeat for one 32-bit payload, so `race_report_mentions` is diagnostic text frequency, not a count of distinct buggy executions.

The recorded environment was x86-64 Linux with GCC 15.2.0 and glibc 2.43. Exact commands, revision, hashes of test source and shared headers, elapsed times, exit codes, and completion status are retained in JSON. Every row requires a normal exit, a `Model-checking complete` marker, and internally consistent counters. The zero-bug rows apply only to the listed finite harnesses under this checker; no unbounded verification or liveness proof is claimed.
