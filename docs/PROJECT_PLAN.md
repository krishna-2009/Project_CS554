# Remaining work

The check-in includes the formal models, finite tests, experiment results,
and progress report. The next stages extend the algorithm coverage and
prepare the final report.

1. Full Dekker turn arbitration, withdrawal, retry, and release behavior.
2. Repeated Peterson acquisitions at explicit bounds.
3. CDSChecker tests for the turn-exchange repair.
4. A simplified RCU grace-period protocol with a reader-safety property.
5. Hand arguments and execution graphs for selected failures and repairs.
6. SPSC slot reuse and wrap-around, if included as a stretch goal.

The existing tests cover bounded safety. Repeated acquisition, full queue
behavior, and liveness require additional models or arguments.
