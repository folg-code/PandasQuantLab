def informative(timeframe: str):
    """
    Decorator used by strategies to declare informative timeframes.
    """
    def decorator(fn):
        fn._informative = True
        fn._informative_timeframe = timeframe
        return fn
    return decorator