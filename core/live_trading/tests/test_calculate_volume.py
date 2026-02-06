from core.live_trading.execution.risk.sizing import LiveSizer


def test_calculate_volume_positive(mocker):
    mocker.patch(
        "core.live_trading.execution.risk.sizing.LiveSizer.get_account_size",
        return_value=10_000,
    )

    mocker.patch(
        "core.live_trading.execution.risk.sizing.Mt5RiskParams.get_symbol_risk_params",
        return_value=(0.0001, 10),
    )

    vol = LiveSizer.calculate_volume(
        symbol="EURUSD",
        entry_price=1.2000,
        sl=1.1900,
        max_risk=0.01,
    )

    assert vol > 0