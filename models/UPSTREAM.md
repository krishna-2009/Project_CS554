# Reused upstream models

`sc.cat`, `tso.cat`, and `x86tso.cat` are unmodified copies from herdtools7 7.58, commit `1ca343e16a2038e406d1ac674e7e3a1b722b36c7`, `herd/libdir/`. Their includes are resolved using the matching upstream `herd/libdir` (`herd7 -I vendor/herdtools7/herd/libdir`). The project's primary TSO model is `tso.cat`; `x86tso.cat` is retained for comparison only.

Upstream: https://github.com/herd/herdtools7/tree/7.58/herd/libdir
License: CeCILL-B; see vendor/herdtools7/LICENSE.txt.

The x86 litmus files test fixed, single-pass entry fragments. `dekker_entry` contains only Dekker's initial flag doorway, not its turn-based backoff/retry algorithm. Peterson's primary condition checks the full conjunction of both entry conditions; `peterson_both_zero` is only a sufficient diagnostic subset. No release/reset is modeled, so two successful entries cannot be explained by sequential critical sections. MFENCE is tested under SC/TSO only.

The compact vendor tree contains the executable, matching library, license, and
revision. Full source is retrievable at the pinned commit; rebuild instructions
and custom RA/SRA scope are in `docs/HERD.md`. The bundled executable needs
Linux x86-64 with glibc >= 2.42; rebuild it on older systems.
