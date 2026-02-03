```mermaid
flowchart TB
    %% ===== Nodes =====
    U[Caller / Runner] --> P[DefaultOhlcvDataProvider.get_ohlcv]

    P -->|1 cache.coverage symbol, timeframe| C[MarketDataCache]
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

## Backend

Backend to źródło danych. Jedna odpowiedzialność:
  - „Daj mi surowe OHLCV dla symbolu, timeframe i zakresu czasu.”

Przykłady:

  - Mt5Backend
  - DukascopyBackend

Backend:
 - nie wie nic o cache
 - nie wie nic o backteście
 - nie decyduje czy fetchować — tylko jak
 - Nie potrzebuje dziedziczenia.

##Provider
Provider to orchestrator:
    „Sprawdź cache → oblicz braki → dociągnij dane → sklej wynik”

DefaultOhlcvDataProvider:
 - posiada backend (self.backend)
 - posiada cache (self.cache)
 - używa ich przez kontrakt (Protocol)
To jest kompozycja, nie dziedziczenie.