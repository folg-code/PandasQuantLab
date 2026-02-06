from contextlib import contextmanager
import cProfile
import pstats


@contextmanager
def profiling(enabled: bool, path):
    if not enabled:
        yield
        return

    pr = cProfile.Profile()
    pr.enable()
    yield
    pr.disable()
    stats = pstats.Stats(pr)
    stats.sort_stats("cumtime")
    stats.dump_stats(path)