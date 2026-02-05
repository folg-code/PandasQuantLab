import pandas as pd
import pytest

from core.strategy.plan_builder import (
    PlanBuildContext,
    build_trade_plan_from_row,
    build_plans_frame,
)
from core.strategy.trade_plan import FixedExitPlan, ManagedExitPlan


def _ctx(**cfg):
    return PlanBuildContext(
        symbol="EURUSD",
        strategy_name="DummyStrategy",
        strategy_config=cfg,
    )


def _row(
    *,
    close=1.2345,
    signal_entry=None,
    levels=None,
    signal_exit=None,
    custom_stop_loss=None,
):
    return pd.Series(
        {
            "close": close,
            "signal_entry": signal_entry,
            "levels": levels,
            "signal_exit": signal_exit,
            "custom_stop_loss": custom_stop_loss,
        }
    )


def _levels_fixed(sl=1.2, tp1=1.3, tp2=1.4, *, tags=True):
    def node(level, tag):
        return {"level": level, "tag": tag} if tags else {"level": level}

    return {
        "SL": node(sl, "sl_tag"),
        "TP1": node(tp1, "tp1_tag"),
        "TP2": node(tp2, "tp2_tag"),
    }


def _levels_indexed(sl=1.2, tp1=1.3, tp2=1.4):
    # supports fallback: SL->0, TP1->1, TP2->2
    return {
        0: {"level": sl, "tag": "sl_tag"},
        1: {"level": tp1, "tag": "tp1_tag"},
        2: {"level": tp2, "tag": "tp2_tag"},
    }


# ==========================================================
# build_trade_plan_from_row
# ==========================================================

def test_build_trade_plan_returns_none_when_no_signal_or_levels():
    ctx = _ctx()

    assert build_trade_plan_from_row(row=_row(signal_entry=None, levels=_levels_fixed()), ctx=ctx) is None
    assert build_trade_plan_from_row(row=_row(signal_entry={"direction": "long", "tag": "x"}, levels=None), ctx=ctx) is None
    assert build_trade_plan_from_row(row=_row(signal_entry="bad", levels=_levels_fixed()), ctx=ctx) is None


def test_build_trade_plan_returns_none_when_direction_invalid():
    ctx = _ctx()
    row = _row(signal_entry={"direction": "sideways", "tag": "x"}, levels=_levels_fixed())
    assert build_trade_plan_from_row(row=row, ctx=ctx) is None


def test_build_trade_plan_requires_sl():
    ctx = _ctx()
    lv = _levels_fixed()
    del lv["SL"]

    row = _row(signal_entry={"direction": "long", "tag": "x"}, levels=lv)
    assert build_trade_plan_from_row(row=row, ctx=ctx) is None


def test_build_trade_plan_fixed_requires_tp1_and_tp2():
    ctx = _ctx(USE_TRAILING=False)
    lv = {"SL": {"level": 1.2}, "TP1": {"level": 1.3}}  # no TP2

    row = _row(signal_entry={"direction": "long", "tag": "x"}, levels=lv)
    assert build_trade_plan_from_row(row=row, ctx=ctx) is None


def test_build_trade_plan_builds_fixed_exit_plan():
    ctx = _ctx(USE_TRAILING=False)
    row = _row(
        close=1.5,
        signal_entry={"direction": "long", "tag": "entry_tag"},
        levels=_levels_fixed(sl=1.0, tp1=2.0, tp2=3.0),
    )

    plan = build_trade_plan_from_row(row=row, ctx=ctx)
    assert plan is not None
    assert plan.symbol == "EURUSD"
    assert plan.direction == "long"
    assert plan.entry_price == 1.5
    assert plan.entry_tag == "entry_tag"
    assert plan.volume == 0.0
    assert plan.strategy_name == "DummyStrategy"
    assert isinstance(plan.exit_plan, FixedExitPlan)
    assert plan.exit_plan.sl == 1.0
    assert plan.exit_plan.tp1 == 2.0
    assert plan.exit_plan.tp2 == 3.0


@pytest.mark.parametrize(
    "cfg, signal_exit, custom_sl, expect_managed",
    [
        ({"USE_TRAILING": True}, None, None, True),
        ({"USE_TRAILING": False}, {"direction": "close"}, None, True),
        ({"USE_TRAILING": False}, None, {"level": 1.1}, True),
        ({"USE_TRAILING": False}, None, None, False),
    ],
)
def test_build_trade_plan_managed_detection(cfg, signal_exit, custom_sl, expect_managed):
    ctx = _ctx(**cfg)
    row = _row(
        close=1.5,
        signal_entry={"direction": "long", "tag": "x"},
        levels=_levels_fixed(sl=1.0, tp1=2.0, tp2=3.0),
        signal_exit=signal_exit,
        custom_stop_loss=custom_sl,
    )

    plan = build_trade_plan_from_row(row=row, ctx=ctx)
    assert plan is not None
    assert isinstance(plan.exit_plan, ManagedExitPlan) == expect_managed


def test_build_trade_plan_supports_indexed_levels_fallback():
    ctx = _ctx(USE_TRAILING=False)
    row = _row(
        close=1.5,
        signal_entry={"direction": "short", "tag": "x"},
        levels=_levels_indexed(sl=1.0, tp1=0.9, tp2=0.8),
    )

    plan = build_trade_plan_from_row(row=row, ctx=ctx)
    assert plan is not None
    assert plan.direction == "short"
    assert isinstance(plan.exit_plan, FixedExitPlan)
    assert plan.exit_plan.sl == 1.0
    assert plan.exit_plan.tp1 == 0.9
    assert plan.exit_plan.tp2 == 0.8


# ==========================================================
# build_plans_frame
# ==========================================================

def test_build_plans_frame_shape_and_columns():
    ctx = _ctx(USE_TRAILING=False)

    df = pd.DataFrame(
        {
            "close": [1.0, 2.0],
            "signal_entry": [
                {"direction": "long", "tag": "A"},
                None,
            ],
            "levels": [
                _levels_fixed(sl=0.9, tp1=1.1, tp2=1.2),
                None,
            ],
        }
    )

    plans = build_plans_frame(df=df, ctx=ctx, allow_managed_in_backtest=False)

    expected_cols = {
        "plan_valid",
        "plan_direction",
        "plan_entry_tag",
        "plan_entry_price",
        "plan_sl",
        "plan_tp1",
        "plan_tp2",
        "plan_exit_mode",
        "plan_sl_tag",
        "plan_tp1_tag",
        "plan_tp2_tag",
    }
    assert expected_cols.issubset(set(plans.columns))
    assert len(plans) == 2


def test_build_plans_frame_valid_fixed_only_by_default():
    ctx = _ctx(USE_TRAILING=False)

    df = pd.DataFrame(
        {
            "close": [1.0, 2.0, 3.0],
            "signal_entry": [
                {"direction": "long", "tag": "A"},
                {"direction": "long", "tag": "B"},
                {"direction": "short", "tag": "C"},
            ],
            "levels": [
                _levels_fixed(sl=0.9, tp1=1.1, tp2=1.2),  # valid fixed
                {"SL": {"level": 1.5}, "TP1": {"level": 2.5}},  # missing TP2 => invalid fixed
                _levels_fixed(sl=3.2, tp1=3.0, tp2=2.8),  # valid fixed (short)
            ],
            "signal_exit": [None, {"direction": "close"}, None],
            "custom_stop_loss": [None, None, None],
        }
    )

    plans = build_plans_frame(df=df, ctx=ctx, allow_managed_in_backtest=False)

    assert plans.loc[0, "plan_valid"] == True
    assert plans.loc[0, "plan_exit_mode"] == "fixed"

    assert plans.loc[1, "plan_valid"] == False
    assert plans.loc[1, "plan_exit_mode"] is None

    assert plans.loc[2, "plan_valid"] == True
    assert plans.loc[2, "plan_exit_mode"] == "fixed"


def test_build_plans_frame_can_allow_managed_in_backtest():
    ctx = _ctx(USE_TRAILING=False)

    df = pd.DataFrame(
        {
            "close": [1.0],
            "signal_entry": [{"direction": "long", "tag": "A"}],
            "levels": [{"SL": {"level": 0.9}}],
            "signal_exit": [{"direction": "close"}],
            "custom_stop_loss": [None],
        }
    )

    plans = build_plans_frame(df=df, ctx=ctx, allow_managed_in_backtest=True)
    assert plans.loc[0, "plan_valid"] == True
    assert plans.loc[0, "plan_exit_mode"] == "managed"


def test_build_plans_frame_extracts_level_tags():
    ctx = _ctx(USE_TRAILING=False)

    df = pd.DataFrame(
        {
            "close": [1.0],
            "signal_entry": [{"direction": "long", "tag": "A"}],
            "levels": [_levels_fixed(sl=0.9, tp1=1.1, tp2=1.2, tags=True)],
        }
    )

    plans = build_plans_frame(df=df, ctx=ctx, allow_managed_in_backtest=False)
    assert plans.loc[0, "plan_sl_tag"] == "sl_tag"
    assert plans.loc[0, "plan_tp1_tag"] == "tp1_tag"
    assert plans.loc[0, "plan_tp2_tag"] == "tp2_tag"


def test_build_plans_frame_handles_missing_levels_tags_gracefully():
    ctx = _ctx(USE_TRAILING=False)

    df = pd.DataFrame(
        {
            "close": [1.0],
            "signal_entry": [{"direction": "long", "tag": "A"}],
            "levels": [_levels_fixed(tags=False)],  # no 'tag' keys
        }
    )

    plans = build_plans_frame(df=df, ctx=ctx, allow_managed_in_backtest=False)
    assert plans.loc[0, "plan_sl_tag"] == ""
    assert plans.loc[0, "plan_tp1_tag"] == ""
    assert plans.loc[0, "plan_tp2_tag"] == ""