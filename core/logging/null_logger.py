from contextlib import contextmanager


class NullLogger:
    def debug(self, msg: str): pass
    def info(self, msg: str): pass
    def warning(self, msg: str): pass
    def error(self, msg: str): pass
    def log(self, msg: str): pass

    def with_context(self, **ctx):
        return self

    @contextmanager
    def time(self, label: str):
        yield

    @contextmanager
    def section(self, name: str):
        yield

    def get_timings(self) -> dict[str, float]:
        return {}