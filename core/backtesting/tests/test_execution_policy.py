from core.backtesting.execution_policy import ExecutionPolicy, EXEC_MARKET, EXEC_LIMIT


def test_exit_signal_forces_market_exit():
    policy = ExecutionPolicy()

    out = policy.classify_exit_type(
        exit_reason="TP2",
        has_exit_signal=True,
        exit_signal_value=True,
    )

    assert out == EXEC_MARKET


def test_sl_is_market_exit():
    policy = ExecutionPolicy()
    assert policy.classify_exit_type("SL") == EXEC_MARKET


def test_tp2_is_limit_exit():
    policy = ExecutionPolicy()
    assert policy.classify_exit_type("TP2") == EXEC_LIMIT


def test_unknown_reason_fallback():
    policy = ExecutionPolicy(exit_default_type="custom")
    assert policy.classify_exit_type("UNKNOWN") == "custom"