from core.backtesting.execution_policy import EXEC_MARKET, EXEC_LIMIT
from core.backtesting.execution_policy import ExecutionPolicy


def attach_execution_types(
    trade: dict,
    *,
    df,
    execution_policy: ExecutionPolicy,
) -> None:
    """
    Attach execution types (entry / tp1 / exit) to trade dict.

    Execution type describes HOW an order was executed,
    not WHAT happened (that is domain / exit logic).
    """

    exit_reason = trade.get("exit_tag")
    exit_signal_col = getattr(execution_policy, "exit_signal_column", "exit_signal")

    has_exit_signal = bool(df is not None and exit_signal_col in df.columns)

    # IMPORTANT:
    # For now, exit-by-signal is always False.
    # When EXIT_SIGNAL is implemented, this flag must come from simulation.
    exit_signal_value = bool(trade.get("exit_by_signal", False))

    trade["exec_type_entry"] = execution_policy.entry_type
    trade["exec_type_tp1"] = (
        execution_policy.tp_type if trade.get("tp1_time") is not None else None
    )

    trade["exec_type_exit"] = execution_policy.classify_exit_type(
        exit_reason=exit_reason,
        has_exit_signal=has_exit_signal,
        exit_signal_value=exit_signal_value,
    )