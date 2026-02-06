from core.live_trading.engine import LiveEngine


def test_live_engine_calls_on_tick_every_loop(mocker, fixed_now):
    market = mocker.Mock()
    market.poll.return_value = {
        "price": 100.0,
        "time": fixed_now,
        "candle_time": None,
    }

    pm = mocker.Mock()
    runner = mocker.Mock()

    engine = LiveEngine(
        position_manager=pm,
        market_state_provider=market,
        strategy_runner=runner,
        tick_interval_sec=0,
    )

    engine._tick()

    pm.on_tick.assert_called_once()
    runner.run.assert_not_called()

def test_strategy_runs_only_on_new_candle(mocker, fixed_now):
    market = mocker.Mock()
    market.poll.return_value = {
        "price": 100.0,
        "time": fixed_now,
        "candle_time": fixed_now,
    }

    pm = mocker.Mock()
    runner = mocker.Mock()
    runner.run.return_value = mocker.Mock(plan=None, last_row={})

    engine = LiveEngine(
        position_manager=pm,
        market_state_provider=market,
        strategy_runner=runner,
        tick_interval_sec=0,
    )

    engine._tick()

    runner.run.assert_called_once()

def test_engine_skips_when_market_state_none(mocker):
    market = mocker.Mock()
    market.poll.return_value = None

    pm = mocker.Mock()
    runner = mocker.Mock()

    engine = LiveEngine(
        position_manager=pm,
        market_state_provider=market,
        strategy_runner=runner,
        tick_interval_sec=0,
    )

    engine._tick()

    pm.on_tick.assert_not_called()
    runner.run.assert_not_called()