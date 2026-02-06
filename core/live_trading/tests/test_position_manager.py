from core.live_trading.execution.position_manager import PositionManager


def test_position_manager_blocks_duplicate_entry(mocker):
    repo = mocker.Mock()
    repo.load_active.return_value = {"1": {"symbol": "EURUSD"}}

    adapter = mocker.Mock()
    pm = PositionManager(repo=repo, adapter=adapter)

    plan = mocker.Mock(symbol="EURUSD")

    pm.on_trade_plan(plan=plan, market_state={})

    adapter.open_position.assert_not_called()

def test_exit_on_sl(mocker, fixed_now):
    repo = mocker.Mock()
    repo.load_active.return_value = {
        "1": {
            "trade_id": "1",
            "direction": "long",
            "sl": 99.0,
            "tp2": None,
            "entry_time": fixed_now,
            "ticket": "1",
        }
    }

    adapter = mocker.Mock(dry_run=True)
    pm = PositionManager(repo=repo, adapter=adapter)

    pm.on_tick(
        market_state={
            "price": 98.0,
            "time": fixed_now,
        }
    )

    repo.record_exit.assert_called_once()

def test_tp1_partial_and_be(mocker, fixed_now):
    repo = mocker.Mock()
    repo.load_active.return_value = {
        "1": {
            "trade_id": "1",
            "direction": "long",
            "entry_price": 100,
            "sl": 95,
            "tp1": 105,
            "tp1_executed": False,
            "volume": 1.0,
            "ticket": "1",
            "strategy_config": {"TP1_CLOSE_RATIO": 0.5},
        }
    }

    adapter = mocker.Mock(dry_run=True)
    pm = PositionManager(repo=repo, adapter=adapter)

    # 🔧 KLUCZOWE: podmieniamy state
    pm.state = mocker.Mock()

    pm.on_tick(
        market_state={
            "price": 106,
            "time": fixed_now,
        }
    )

    pm.state.mark_tp1_executed.assert_called_once()