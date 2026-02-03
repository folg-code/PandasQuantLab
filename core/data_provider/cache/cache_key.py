from pathlib import Path


def build_cache_key(root, symbol: str, timeframe: str) -> Path:
    return root / f"{symbol}_{timeframe}.csv"