# Model and test design

## Memory models

SC uses the existing herdtools7 model, and x86-TSO uses the upstream hardware
model. RA and SRA follow the language-level fragment in Lahav, Giannarakis,
and Vafeiadis: ordinary reads are acquire, writes are release, and updates are
acquire-release. The paper defines updates as combined events; herd splits
them into read and write events connected by `rmw`.

The implemented RA model uses:

```cat
include "cos.cat"
let sb = po | rmw
let hb = (sb | rf)+
let hb_loc = hb & loc
acyclic sb | rf as hb_acyclic
acyclic hb_loc | co | fr as ra_coherence
empty rmw & (fre;coe) as atomic
```

SRA retains those checks and adds `acyclic hb | co`. Here `co` is the union
of per-location modification orders. Complete `hb` paths are computed before
restricting endpoints to a location, preserving paths through other locations.
Calibration checks selected expected behaviors; it does not establish model
equivalence for every program. Definitions and coherence characterization:
[Taming Release-Acquire Consistency](https://plv.mpi-sws.org/sra/full.pdf).

The SC/TSO files and matching includes are pinned upstream copies. The TSO
model includes per-location coherence, atomicity, explicit fences, and implied
barriers. Provenance is in `models/UPSTREAM.md`.

## Fence interpretation

Hardware MFENCE and a language-level acquire-release exchange are different
operations. MFENCE tests use the SC/TSO models. RA/SRA fence experiments use a
separate exchange on a shared dummy location. The paper's fence translation
has placement premises; one exchange placement does not make an arbitrary
program sequentially consistent.

Store buffering, message passing, 2+2W, and store buffering with dummy exchanges
calibrate the models. The Peterson tests additionally show that blocking the
both-zero flag outcome is weaker than blocking the full admission condition.

## Safety properties

- **Peterson:** both entry predicates must hold for the queried violation.
  The predicate is `(a == 0 || b == 0) && (c == 0 || d == 1)`, where `a,c`
  are other-flag reads and `b,d` are turn reads. Flags remain set in the
  fragment, so both successful decisions conflict.
- **Dekker:** the present test covers the initial flag doorway. Withdrawal,
  turn arbitration, retry, and release are outside that fragment.
- **RMW locks:** the payload invariant is symmetric in acquisition order.
  A stale read is not itself a failure if the reader legitimately acquires
  before the writer.
- **Race detection:** an unordered non-atomic conflict is distinct from
  simultaneous critical-section occupancy. Separate admission assertions
  avoid adding a shared monitoring RMW that could strengthen synchronization.
- **RCU:** the relevant extension is reader safety across reclamation after a
  grace period. Concurrent readers are part of the protocol.
- **SPSC:** the current harness checks one-item publication. Slot reuse,
  wrap-around, and empty/full behavior remain outside its scope.

## C11/C++11 implementation

CDSChecker tests use its `user_main` entry point and supplied atomic/thread
headers. Non-atomic accesses are instrumented through `librace.h`; assertions
use `MODEL_ASSERT`. Release stores and acquire loads are valid plain
operations; acquire-release ordering applies to suitable RMWs.

The checker is a historical C11/C++11 implementation. Finite tests and the
checker options define the exploration scope. Complete bug-free, buggy,
redundant, and infeasible counts are retained separately; total executions
include checker overhead. A byte-address race diagnostic can report multiple
bytes of one conflicting object. See the [CDSChecker documentation](https://github.com/computersforpeace/model-checker)
and its [limitations](https://plrg.eecs.uci.edu/publications/toplas16.pdf).

## Result interpretation

Herd's `Positive` and `Negative` values count execution witnesses for the
condition. `States` counts observed register/location projections. The header
`Test ... Allowed` alone does not determine whether the queried outcome is
reachable. Tool errors and timeouts are separate from forbidden outcomes.
Raw logs, source hashes, tool versions, and exact commands accompany the
summaries. See the [herd7 manual](https://diy.inria.fr/doc/herd.html).
