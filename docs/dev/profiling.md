# Profiling and performance workflow

Performance is treated as an engineering concern:
measure first, optimize second.

---

## Principles

- Prefer vectorized pandas over row-wise loops
- Reduce dataframe copies and intermediate allocations
- Cache intermediate results via DAG context
- Use numba only for identified hot paths

---

## What to measure

- total pipeline runtime (end-to-end)
- feature module runtime distribution
- strategy runtime
- execution engine runtime
- peak memory usage (large datasets)

---

## Practical workflow

1) Run a small dataset to validate correctness.
2) Run a medium dataset to locate hotspots.
3) Profile the hottest functions/modules.
4) Optimize one hotspot at a time.
5) Re-run with the same input to confirm deterministic behavior.

---

## Benchmark hygiene

When measuring performance:
- use the same dataset and timerange
- disable background tasks
- run multiple times and compare variance
- track results in a simple log or markdown table

---

## Stress tests

Stress tests validate stability under load:
- intentionally high signal density
- large number of trades
- long timeranges

The goal is not “pretty backtest results”.
The goal is stable performance and predictable execution behavior.