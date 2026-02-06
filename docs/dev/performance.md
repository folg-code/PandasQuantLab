# Performance & Profiling

This document describes **observed performance characteristics**, profiling results
and optimization strategy of the framework.

Performance is treated as a **first-class architectural concern**, not as an afterthought.

---

## Test scenario

Representative backtest run used for profiling:

- Symbols: 2 (EURUSD, XAUUSD)
- Base timeframe: M1
- Informative timeframe: M30
- Historical range: ~6 years
- OHLCV rows:
  - ~520k bars per symbol (M1)
  - ~18k bars per symbol (M30)
- Strategy:
  - multi-timeframe
  - feature-heavy (market structure, volatility, regimes)
- Execution:
  - full cost model
  - parallel backtest execution

---

## End-to-end runtime breakdown

Measured wall-clock times (single run):

| Stage                           | Time     |
|---------------------------------|----------|
| Data loading & caching          | ~22s     |
| Strategy execution (features + signals + plans) | ~25s     |
| Backtest execution (parallel)  | ~1.9s    |
| Reporting & persistence         | <1s      |
| **Total runtime**               | **~50s** |

Timing is collected using structured instrumentation across pipeline stages.

---

## Profiling methodology

Profiling was performed using Python `cProfile` with cumulative time analysis:

- Full pipeline profiling (not isolated microbenchmarks)
- Focus on **hot paths**, not function call counts
- Profiling reflects **real workload**, not synthetic data

---

## Profiling summary (high level)

Profiling confirms that execution time is dominated by **expected domains**:

1. **Data access & preprocessing**
   - Historical OHLCV loading
   - Cache merging and validation

2. **Feature engineering**
   - Market structure analysis
   - Dependency-aware feature computation

3. **Vectorized pandas operations**
   - Series access
   - Column-wise transformations

Orchestration, execution control flow and trade simulation introduce **negligible overhead**.

This validates the architectural separation between:
- deterministic computation
- orchestration
- execution side effects

---

## Hot paths (qualitative)

Key contributors to cumulative runtime:

- Historical data provider (`fetch`, `_get_ohlcv`)
- Strategy `populate_indicators`
- FeatureEngineering pipeline
- MarketStructureEngine (pivots, price action, regimes)
- Pandas Series access and combination

Notably **absent** from hot paths:

- Strategy orchestration logic
- Execution engine control flow
- Trade repository operations
- Logging and instrumentation

This indicates a **healthy performance profile**:
time is spent where domain complexity lives.

---

## Feature engineering cost model

Feature computation dominates strategy runtime by design.

Key properties:

- Deterministic execution order
- Explicit feature dependencies
- No implicit recomputation
- Reusable context across features

Market structure analysis is treated as a **feature extraction problem**,
not as strategy logic, making it:

- measurable
- optimizable
- replaceable

---

## Pandas overhead

Profiling shows measurable overhead in:

- `Series.__getitem__`
- `Series.combine`
- Generic dataframe access

This overhead is:
- explicit
- measurable
- localized to feature computation

It does **not** leak into orchestration or execution layers.

---

## Optimization strategy

Optimization is intentionally **incremental and targeted**.

Planned directions:

1. **Numba acceleration**
   - Only for confirmed hot paths
   - Focus on pivot detection and structural calculations
   - Preserve deterministic semantics

2. **Data representation**
   - Evaluate narrower arrays for selected features
   - Avoid premature rewrites

3. **Batch execution**
   - Reuse intermediate feature context where possible
   - Avoid recomputation across symbols and timeframes

Because hot paths are explicitly identified,
optimization can be applied without architectural refactors.

---

## Design takeaway

Profiling confirms that:

- Architecture scales as intended
- Performance cost is dominated by domain logic, not framework overhead
- Feature engineering is the correct optimization target
- Execution and orchestration layers remain lightweight

This allows performance work to proceed **safely and predictably**,
without compromising correctness or determinism.

---

## Notes

Performance measurements are hardware-dependent and provided for
architectural insight rather than absolute benchmarking.

All measurements were obtained from real end-to-end runs.