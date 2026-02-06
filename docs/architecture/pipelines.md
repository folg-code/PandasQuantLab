# Pipelines (backtest and live)

This document contains the detailed runner flows.  
README intentionally keeps pipelines simplified.

---

## BacktestRunner — detailed flow

```mermaid
flowchart LR

    RUN[BacktestRunner.run]

    RUN --> DATA[Data Loading]
    DATA --> STRAT[Strategy Execution]
    STRAT --> BT[Backtesting Engine]
    BT --> RES[Result Build]
    RES --> REP[Reporting]

    subgraph DATA[Data Layer]
        DL1[BacktestStrategyDataProvider]
        DL2[CsvMarketDataCache]
        DL3[Backend Fetch]
        DL1 --> DL2
        DL1 --> DL3
    end

    subgraph STRAT[Strategy Layer]
        S1[run_strategies]
        S2[run_strategy_single / parallel]
        S3[apply_informatives]
        S4[populate_indicators]
        S5[populate_entry_trend]
        S6[populate_exit_trend]
        S7[build_trade_plans]

        S1 --> S2
        S2 --> S3 --> S4 --> S5 --> S6 --> S7
    end

    subgraph BT[Execution Layer]
        B1[Backtester]
        B2[run_backtests_single / parallel]
        B4[execution_loop]

        B2 --> B1
        B1 --> B4
    end

    subgraph REP[Reporting Layer]
        R1[ReportRunner]
        R2[Per‑symbol reports]
        R3[SummaryReportRunner]

        R1 --> R2
        R1 --> R3
    end
```
---

## LiveTradingRunner — detailed flow
```mermaid
flowchart LR

    %% =================================================
    %% ENTRY POINT
    %% =================================================
    A[LiveTradingRunner.run]

    %% =================================================
    %% INIT SECTION
    %% =================================================
    subgraph INIT[Initialization]

        B[MT5 initialize]
        C[Symbol select]
        D[Load Strategy Class]
        E[Build Live Logger]

    end

    A --> INIT
    INIT --> B --> C
    INIT --> D
    INIT --> E

    %% =================================================
    %% DATA LAYER
    %% =================================================
    subgraph DATA[Data Layer]

        F[Strategy declares required timeframes]
        G[MT5Client]
        H[LiveStrategyDataProvider]
        I[MT5MarketStateProvider]

    end

    D --> F
    G --> H
    F --> H
    A --> H
    A --> I

    %% =================================================
    %% STRATEGY LAYER
    %% =================================================
    subgraph STRATEGY[Strategy Layer]

        J[LiveStrategyRunner]

        subgraph DOMAIN[Strategy Domain *shared with backtest*]

            K[apply_informatives]
            L[populate_indicators]
            M[populate_entry_trend]
            N[populate_exit_trend]
            O[build_trade_plans]

            K --> L --> M --> N --> O
        end

    end

    H --> J
    D --> J
    J --> K

    %% =================================================
    %% EXECUTION LAYER
    %% =================================================
    subgraph EXECUTION[Execution Layer]

        P[LiveEngine]
        Q[PositionManager]
        R[TradeRepo / TradeStateService]
        S[MT5Adapter]
        T[MetaTrader5 API]

    end

    %% =================================================
    %% RUNTIME FLOW
    %% =================================================

    %% Market state into engine
    I --> P

    %% Trade plans into engine
    O --> P

    %% Engine orchestration
    P --> Q
    Q --> R
    Q --> S
    S --> T

    %% =================================================
    %% FEEDBACK LOOPS
    %% =================================================

    T -->|broker-driven exits| Q
    P -->|tick loop| P
```

## BacktestDataProvider — detailed flow
```mermaid
flowchart TB
    %% ===== Nodes =====
    U[Caller / Runner] --> P[BacktestStrategyDataProvider.get_ohlcv]

    P -->|1 cache.coverage symbol, timeframe| C[CsvMarketDataCache]
    C -->|returns: None or cov_start, cov_end| P

    %% ===== Decision: cache coverage =====
    P --> D1{Coverage exists?}

    D1 -- No --> B1[backend.fetch_ohlcv full range]
    B1 --> N1[_validate/_normalize provider-side]
    N1 -->|cache.save... if fetched| C
    N1 --> R1[return merged DF]

    D1 -- Yes --> D2{Missing pre-range?}
    D2 -- Yes --> B2[backend.fetch_ohlcv pre range]
    B2 --> N2[_validate/_normalize]
    N2 -->|cache.append pre if non-empty| C

    D2 -- No --> D3{Missing post-range?}

    D3 -- Yes --> B3[backend.fetch_ohlcv post range]
    B3 --> N3[_validate/_normalize]
    N3 -->|cache.append post if non-empty| C

    %% ===== Load middle part =====
    D3 -- No --> M[cache.load_range requested range]
    N2 --> M
    N3 --> M

    M --> R2[merge pre + mid + post]
    R2 --> R3[return merged DF]
```