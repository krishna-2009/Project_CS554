# Herd7 toolchain and formal scope

The bundled Linux x86-64 executable is herdtools7 7.58 at commit
`1ca343e16a2038e406d1ac674e7e3a1b722b36c7` (tag `7.58`).
Upstream: https://github.com/herd/herdtools7/tree/7.58

The runtime retains the upstream CeCILL-B license. `models/sc.cat`,
`models/tso.cat`, and `models/x86tso.cat` are byte-for-byte upstream copies.
`sc.cat` and `tso.cat` are used in the main matrix. Their library includes
are the matching unmodified `vendor/herdtools7/herd/libdir`.

## Run

From the project root:

```bash
python3 scripts/run_herd.py --graphs
```

The runner uses `HERD7` if set, then installed `herd7` on PATH, then the bundled
`vendor/herdtools7/bin/herd7`. Every invocation explicitly selects the pinned
model include directories. It writes `results/herd_summary.json`, exact raw
outputs in `results/herd_raw/`, and selected witness graphs in
`results/herd_graphs/{tso,ra}/`.

`Positive`/`Negative` count allowed execution witnesses satisfying/not satisfying
the condition. `States` counts distinct projections onto observed registers or
locations, which differ between conditions. No count is an empirical frequency,
a scheduler-path count, or an unbounded proof.

## Rebuild on another Linux distribution

The included binary was built on Ubuntu 26.04 using OCaml 5.4.0, dune 3.20.2,
menhir 20250912, and zarith 1.14. It dynamically links glibc and libgmp;
it requires glibc 2.42 or later. On an older distribution, rebuild locally or
install the pinned tool using opam. The tool requires no external ARM/PowerPC
hardware. A compatible OCaml/opam environment can use:

```bash
opam install dune menhir zarith
bash scripts/build_herd.sh
python3 scripts/run_herd.py --graphs
```

If herdtools7 7.58 is already installed, set `HERD7` to that executable.
The rebuild script clones the public source and checks out the exact commit,
then builds only `herd/herd.exe`; default parallelism is 2. Override
`HERD_BUILD_DIR` and `HERD_BUILD_JOBS` if needed. The build script requires an existing OCaml toolchain.

## Formal interpretations

The SC/TSO rows have their native x86 litmus interpretation. The custom RA/SRA
rows reuse the parser syntax as a compact event-language notation: **each store
is release, each load is acquire, and each exchange is acquire-release**. They
are the mathematical all-acquire/all-release fragment from Lahav et al., not
an assertion that x86 has RA semantics and not the full C11 memory model.
MFENCE has no intrinsic meaning in these custom models; MFENCE tests are
therefore omitted from the RA/SRA matrix.

`ra.cat` computes `sb = po | rmw` because herd represents an atomic exchange as
separate read/write events and `po` alone does not connect its internal pair.
Then `hb=(sb|rf)+`; it checks no-thin-air and
`acyclic (hb & loc) | co | fr`, together with RMW atomicity. The complete `hb`
paths are computed **before** restricting endpoints to the same location.
The last check contracts whole cross-location `sb/rf` paths and implements the
paper's separate coherence condition at each location; simply filtering
`sb|rf` first would miss ordering. `sra.cat` retains these RA checks and adds
`acyclic hb | co`. This `co` is the union of the per-location modification
orders, not an independently chosen global total order.

Primary definitions: https://plv.mpi-sws.org/sra/full.pdf

## Bounds and regression checks

The suite contains fixed two-thread, single-pass entry fragments. There is no
unlock/reset: two successful entries indicate overlapping ownership within
this fragment. It does not check arbitrary retry loops, repeated acquisitions,
starvation, deadlock freedom, or fairness. `dekker_entry` is only the initial
flag doorway, not Dekker's complete backoff protocol. SB, MP, 2+2W, and shared
RMW-fence tests calibrate characteristic behaviors, but these regressions do
not independently prove equivalence to every aspect of a source model.

Peterson's primary condition checks both full entry predicates. The separate
both-zero condition is a sufficient subset only. A shared dummy exchange after
the turn store eliminates both-zero under RA/SRA while leaving two witnesses
for the full predicate. Replacing the turn store itself with an exchange
eliminates the full bad predicate within this bound. These are measured
results; they must not be generalized into a complete lock implementation proof.
