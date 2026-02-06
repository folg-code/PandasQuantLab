import pytest
from core.backtesting.backend_factory import create_backtest_backend
from core.data_provider.backends.dukascopy_backend import DukascopyBackend


def test_create_dukascopy_backend():
    backend = create_backtest_backend("dukascopy")
    assert isinstance(backend, DukascopyBackend)


def test_create_backend_invalid_name():
    with pytest.raises(ValueError):
        create_backtest_backend("invalid_backend")