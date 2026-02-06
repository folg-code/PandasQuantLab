from core.live_trading.execution.live.trade_state_service import TradeStateService


def test_has_active_position_true(mocker):
    repo = mocker.Mock()
    repo.load_active.return_value = {
        "1": {"symbol": "EURUSD"}
    }

    svc = TradeStateService(repo=repo, adapter=mocker.Mock())

    assert svc.has_active_position("EURUSD") is True


def test_update_sl_updates_repo_and_calls_adapter(mocker):
    repo = mocker.Mock()
    repo.load_active.return_value = {
        "1": {"ticket": "1", "sl": 95}
    }

    adapter = mocker.Mock()
    svc = TradeStateService(repo=repo, adapter=adapter)

    svc.update_sl(trade_id="1", new_sl=100)

    adapter.modify_sl.assert_called_once()
    repo.save_active.assert_called_once()