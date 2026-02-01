# Roadmap

This roadmap defines the planned evolution of the framework.
The order is intentional and optimized for:
- fast feedback loops
- architectural correctness
- controlled growth of system complexity
- clear separation between research, analytics, execution and infrastructure

Completed documentation, architecture and reporting foundations are omitted.

---

## Phase 1 — Test Coverage & Validation

**Goal:** Establish confidence and prevent architectural regressions.

- Add comprehensive test coverage:
  - unit tests for feature nodes and pure computations
  - contract tests for adapters and data providers
  - integration tests for pipelines on small, deterministic fixtures
- Add invariant checks:
  - no lookahead bias
  - deterministic outputs for identical inputs
  - schema and contract validation
- Define a minimal CI test suite focused on correctness (not performance)

No new features or refactors in this phase.

---

## Phase 2 — Technical Analysis Refactor Completion

**Goal:** Finalize and stabilize the TechnicalAnalysis module architecture.

- Complete refactor of the TechnicalAnalysis module:
  - finalize module boundaries and responsibilities
  - unify feature interfaces and outputs
  - remove legacy or duplicated logic
- Align all feature modules with the DAG-based execution model
- Ensure full test coverage for the refactored architecture
- Freeze the TechnicalAnalysis API as a stable contract

No new research or feature expansion in this phase.

---

## Phase 3 — Baseline Stabilization

**Goal:** Establish a fixed reference point for further development.

- Freeze:
  - one strategy
  - one market
  - one timeframe
- Define a fixed historical dataset
- Produce a baseline backtest result
- Treat this result as a long-term reference benchmark

This baseline is used for all future comparisons.

---

## Phase 4 — Analytics & Strategy Evaluation

**Goal:** Enable systematic, repeatable strategy evaluation.

- Strategy benchmarking on identical datasets
- Side-by-side comparison of strategy variants
- Metric-level comparisons (returns, drawdowns, expectancy)
- Equity curve overlays and relative performance analysis
- Comparison against simple baselines

Focus on measurement quality, not feature expansion.

---

## Phase 5 — Feature Engineering (Non-ML)

**Goal:** Identify stable and informative features.

- Expand and validate contextual feature sets:
  - market structure
  - regime and volatility context
  - distance and timing-based features
- Analyze feature behavior:
  - stability across time
  - redundancy and correlation
  - conditional expectancy
- Reduce feature set to a small, high-quality core

No machine learning is introduced in this phase.

---

## Phase 6 — Machine Learning as a Filtering Layer

**Goal:** Improve trade selection robustness without altering signal logic.

- Define explicit ML targets
- Train tree-based models (e.g. Random Forest, gradient boosting)
- Perform strict out-of-sample and walk-forward validation
- Integrate ML as a scoring or filtering layer only
- Discard ML if robustness does not improve

ML strengthens decision quality; it does not create signals.

---

## Phase 7 — Market Research Workflow

**Goal:** Formalize hypothesis-driven market research.

- Formulate explicit, testable hypotheses
- Translate hypotheses into measurable features
- Validate ideas using the analytics layer
- Systematically discard non-robust ideas

Research remains subordinate to analytics and validation.

---

## Phase 8 — Execution Layer Expansion & Portability

**Goal:** Production-ready execution independent of platform constraints.

- Add additional broker / execution adapters
- Improve execution safety and rule guards
- Introduce containerized runtime for the engine
- Support live and paper trading consistently
- Add execution health checks and fail-safe mechanisms

Execution logic remains thin, deterministic and broker-agnostic.

---

## Phase 9 — Runtime Control & Monitoring

**Goal:** Safe live operation and supervision.

- Runtime strategy control (enable/disable, pause/resume)
- Manual and emergency trade operations
- Global and per-strategy kill switches
- Event-based notification system
- Configurable alert levels and delivery channels

All runtime control must be auditable and deterministic.

---

## Phase 10 — Backtest vs Live Consistency Validation

**Goal:** Detect execution drift and hidden performance degradation.

- Align backtest, dry-run and live datasets
- Compare execution and performance metrics
- Detect missing or extra trades
- Analyze timing and slippage divergence
- Define acceptable deviation thresholds
- Trigger alerts on significant discrepancies

---

## Phase 11 — Control Plane & Orchestration

**Goal:** Operational usability and orchestration.

- Centralized control plane for strategies and runs
- Management of backtests, reports and runtime state
- UI for operational control and analytics access
- Centralized configuration and notification management

The control plane orchestrates the system; it does not perform computation.

---
