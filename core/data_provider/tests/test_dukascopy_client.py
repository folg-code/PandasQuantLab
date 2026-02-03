import pandas as pd
from core.data_provider.clients.dukascopy import DukascopyClient

def test_parse_dukascopy_time_seconds():
    c = DukascopyClient()
    s = pd.Series([1640995200, 1640995260])
    out = c.parse_dukascopy_time(s)
    assert out.dt.tz is not None

def test_parse_dukascopy_time_millis():
    c = DukascopyClient()
    s = pd.Series([1640995200000, 1640995260000])
    out = c.parse_dukascopy_time(s)
    assert out.dt.tz is not None

def test_parse_dukascopy_time_string():
    c = DukascopyClient()
    s = pd.Series(["2022-01-01T00:00:00Z", "2022-01-01T00:01:00Z"])
    out = c.parse_dukascopy_time(s)
    assert out.dt.tz is not None