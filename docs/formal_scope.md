# Formal scope of the check-in experiments

These experiments check safety of finite event graphs. They do not prove the complete lock implementations.

## Event relations

`po` orders distinct instructions in a thread; `rf` maps writes to reads observing them. `co` is a strict total order on writes at each location, taken together as one relation across all locations. `fr = rf^-1 ; co` relates a read to later writes at its location. Herd uses split read and write events for an atomic update; `rmw` links those two halves.

In the abstract RA/SRA runs, ordinary reads are acquire, ordinary writes are release, and atomic updates are acquire-release. The relations are:

```
sb = po | rmw
hb = (sb | rf)+
hb_loc = hb & loc
```

The internal RMW edge is necessary. In the X86 frontend's XCHG graph, the two halves share an instruction index and have an `rmw`/internal-causality link; distinct-instruction `po` does not itself connect the two halves. The internal edge keeps each update ordered as one atomic operation.

## RA and SRA checks

RA requires:

```
acyclic sb | rf
acyclic hb_loc | co | fr
empty rmw & (fre;coe)
```

SRA retains all three checks and additionally requires:

```
acyclic hb | co
```

For ordinary events, the coherence check follows the per-location characterization in Proposition 2 of Lahav et al. Full `hb` is computed first, so a path through other locations is retained when its endpoints return to the same location. Each location's `co`/`fr` edges can then be connected by those collapsed paths. Global no-thin-air acyclicity remains a separate requirement. The RMW check prevents an update from skipping an intervening external write; initialization, total per-location orders, reads-from candidates, and frontend constraints are supplied by herd and `cos.cat`.

The adaptation from the paper's combined update events to herd's split events is an implementation choice. Calibration establishes selected expected behaviors; it does not prove full equivalence for every program.

Source: Ori Lahav, Nick Giannarakis, and Viktor Vafeiadis, *Taming Release-Acquire Consistency*, POPL 2016, Definitions 4, 5, and 8 and Proposition 2. [Paper](https://plv.mpi-sws.org/sra/full.pdf)

## Bounded Peterson property

Thread 0 executes `flag0=1; turn=1; a=flag1; b=turn`. Thread 1 executes `flag1=1; turn=0; c=flag0; d=turn`. The queried simultaneous-admission condition is:

```
(a == 0 || b == 0) && (c == 0 || d == 1)
```

Flags are never cleared in this prefix, so two successful admission decisions represent incompatible ownership claims. The smaller predicate `a==0 && c==0` is sufficient for a counterexample but misses other failures. The both-zero predicate therefore covers only a subset of admission failures.

This prefix evaluates both loads unconditionally. Actual Peterson code normally short-circuits its wait expression and retries if the condition is true. The prefix can expose a safety failure in an entry attempt; it does not establish correctness of arbitrary retries, unlock behavior, repeated acquisitions, starvation freedom, or fairness.

## Why a single shared dummy update is not automatically enough

An acquire-release exchange on a shared dummy location between the `turn` store and the reads can forbid the both-zero SB witness: the updates form an order, and the update-to-update reads-from edge carries publication in that order. This does not automatically order the earlier competing writes to `turn` in the same direction as the dummy updates. SRA requires acyclic `hb | co`, while SC and TSO enforce stronger constraints involving communication and preserved program order. A cycle using both a cross-thread `co` edge and an `fr` edge can therefore be relevant even when the both-zero diagnostic is forbidden.

For example, consider the abstract shape `W(flag1,1) ->po W(turn,0) ->co W(turn,1) ->hb R(flag1,0) ->fr W(flag1,1)`. Its middle coherence edge is not itself an `hb` edge. Adding one dummy update does not by definition make this a prohibited RA/SRA cycle. The full-predicate tests distinguish this placement from a sufficient repair.

An independent check of the observed witness uses combined update events:

| Thread 0 | Thread 1 |
|---|---|
| A: `W(flag0,1)` | H: `W(flag1,1)` |
| B: `W(turn,1)` | I: `W(turn,0)` |
| F0: `U(f,0,0)` | F1: `U(f,0,0)` |
| E: `R(flag1,0)` | M: `R(flag0,1)` |
| G: `R(turn,1)` | N: `R(turn,1)` |

The witness uses `I ->co B`, `F0 ->co F1`, and reads-from edges `F0 ->rf F1`, `init(flag1) ->rf E`, `A ->rf M`, and `B ->rf G,N`. F0 reads initial `f=0`. The order `H,I,A,B,F0,E,G,F1,M,N`, with initialization first, is a topological order for `hb | co`. Each location's coherence condition is also satisfied. Both entry predicates hold. The reader E observes an overwritten flag in this displayed global order, but that display is an order for SRA's `hb | co`, not an SC execution: SRA does not add every `fr` edge to its global check. The cycle above explains the distinction. This small witness validates the interpretation of the bounded checker result without asserting anything about a full retrying implementation.

Replacing competing plain `turn` stores with acquire-release RMWs gives a distinct algorithm variant. Its zero-witness result applies only to the tested fragment and is separate from the dummy-location and hardware-MFENCE results.

## What remains for the final report

Remaining extensions include full acquisition/release control flow, repeated acquisitions, matching C11 tests, RCU safe reclamation, and optional SPSC reuse cases. Safety and liveness are separate properties. A run with no witnesses means that the queried outcome is forbidden for the supplied finite test and model, not that every implementation of the named algorithm has been proved correct.
