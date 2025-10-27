from functools import wraps

def informative(timeframe):
    def decorator(func):
        func._informative = True
        func._informative_timeframe = timeframe
        return func
    return decorator