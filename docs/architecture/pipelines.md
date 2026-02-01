# Pipelines (backtest and live)

This document contains the detailed runner flows.  
README intentionally keeps pipelines simplified.

---

## BacktestRunner — detailed flow

```mermaid
flowchart LR
  A[run] --> D

  %% =====================
  %% DATA
  %% =====================
  subgraph D[Data Layer]
    D1[Create backend] --> D2[OHLCV Provider + Cache]
    D2 --> D3[Load OHLCV<br/>per symbol]
    D3 --> D4[all_data]
  end

  %% =====================
  %% STRATEGY
  %% =====================
  D4 --> S
  subgraph S[Strategy Layer]
    S1{Single / Multi symbol?}
    S2[run_strategy_single]
    S3[Parallel execution<br/>ProcessPoolExecutor]
    S4[signals_df]
    S5[return dataframe<br/>with entry signals<br/>and exit plan]

    S1 -->|single| S2 --> S4
    S1 -->|multi| S3 --> S4
    S4 --> S5
  end

  %% =====================
  %% RESEARCH PLOT MODE
  %% =====================
  S --> P{Plot charts<br/>symbol only<br/>research mode}
  P -->|yes| PL[Plot charts<br/>PNG artifacts]
  PL --> END1[Exit]

  %% =====================
  %% BACKTEST
  %% =====================
  P -->|no| B
  subgraph B[Execution / Backtest]
    B1{BACKTEST_MODE}
    B2[Single window]
    B3[Split windows]
    B4[Backtester.run]
    B5[return dataframe<br/>with trades]

    B1 -->|single| B2 --> B4
    B1 -->|split| B3 --> B4
    B4 --> B5
  end

  %% =====================
  %% REPORT
  %% =====================
  B --> R{Generate report?}
  R -->|no| END2[Exit: backtest only]
  R -->|yes| REP

  subgraph REP[Risk & Reporting]
    R1[RiskDataPreparer]
    R2[TradeContextEnricher]
    R3[ReportRunner]
    R4[Metrics, tables, charts]
    R5[render reports:<br/>stdout tables or html dashboard]

    R1 --> R2 --> R3 --> R4 --> R5
  end

  R5 --> END3[Exit: full run]
```
---

## LiveTradingRunner — detailed flow
```mermaid
flowchart LR
  A[run] --> M

  %% =====================
  %% MT5 INIT
  %% =====================
  subgraph M[MT5 Init]
    M1[mt5.initialize] --> M2[symbol_select]
    M2 --> M3[account_info<br/>log balance]
  end

  %% =====================
  %% WARMUP DATA
  %% =====================
  M --> W
  subgraph W[Warmup Data]
    W1[Resolve timeframe + lookback] --> W2[copy_rates_from_pos<br/>bars]
    W2 --> W3[Build DataFrame<br/>UTC time]
    W3 --> W4[df_ltf]
  end

  %% =====================
  %% INFORMATIVE PROVIDER
  %% =====================
  W4 --> I
  subgraph I[Informative Provider]
    I1[load_strategy_class] --> I2[get_required_informatives]
    I2 --> I3[compute bars_per_tf<br/>lookback + MIN_HTF_BARS]
    I3 --> I4[LiveMT5Provider<br/>bars_per_tf]
  end

  %% =====================
  %% STRATEGY
  %% =====================
  I4 --> S
  W4 --> S
  subgraph S[Strategy Layer]
    S1[load_strategy<br/>df_ltf + symbol + startup_candle_count] --> S2[strategy]
  end

  %% =====================
  %% ENGINE BUILD
  %% =====================
  S2 --> E
  subgraph E[Execution / Live Engine]
    E1[MT5Adapter<br/>dry_run flag]
    E2[TradeRepo]
    E3[PositionManager<br/>repo + adapter]
    E4[LiveStrategyAdapter<br/>wrap strategy]
    E5[market_data_provider<br/>last closed candle]
    E6[LiveEngine<br/>tick_interval_sec]

    E1 --> E3
    E2 --> E3
    E4 --> E6
    E5 --> E6
    E3 --> E6
  end

  %% =====================
  %% RUN LOOP (conceptual)
  %% =====================
  E --> R
  subgraph R[Run Loop]
    R1[engine.start] --> R2{Tick}
    R2 --> R3[market_data_provider]
    R3 --> R4[strategy_adapter<br/>intents]
    R4 --> R5[position_manager<br/>orders/positions]
    R5 --> R2
  end
```