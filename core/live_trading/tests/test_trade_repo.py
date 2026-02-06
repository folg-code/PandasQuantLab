from datetime import datetime

from core.live_trading.trade_repo import TradeRepo


def test_trade_repo_is_restart_safe(tmp_path):
    repo = TradeRepo(data_dir=tmp_path)

    repo.record_entry(
        trade_id="1",
        symbol="EURUSD",
        direction="long",
        entry_price=100,
        volume=1,
        sl=95,
        tp1=105,
        tp2=110,
        entry_time=datetime.utcnow(),
        entry_tag="test",
    )

    repo2 = TradeRepo(data_dir=tmp_path)

    active = repo2.load_active()
    assert "1" in active