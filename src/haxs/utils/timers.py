from __future__ import annotations
from contextlib import contextmanager
from time import perf_counter

@contextmanager
def timed() -> dict[str, float]:
    box: dict[str, float] = {"elapsed_s": 0.0}
    start = perf_counter()
    try:
        yield box
    finally:
        box["elapsed_s"] = perf_counter() - start
