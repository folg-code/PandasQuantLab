from core.live_trading.engine import LiveEngine


def test_live_engine_full_flow(mocker, fixed_now):
    market = mocker.Mock()
    market.poll.return_value = {
        "price": 100,
        "time": fixed_now,
        "candle_time": fixed_now,
    }

    pm = mocker.Mock()
    runner = mocker.Mock()
    runner.run.return_value = mocker.Mock(plan="PLAN", last_row={})

    engine = LiveEngine(
        position_manager=pm,
        market_state_provider=market,
        strategy_runner=runner,
        tick_interval_sec=0,
    )

    engine._tick()

    pm.on_trade_plan.assert_called_once()