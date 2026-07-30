from __future__ import annotations
import hashlib
import numpy as np

DEFAULT_SEED = 1729

def seed_from_items(*items: object) -> int:
    text = "|".join(map(str, items)).encode("utf-8")
    return int(hashlib.sha256(text).hexdigest()[:12], 16) % (2**32 - 1)

def rng(seed: int | None = None) -> np.random.Generator:
    return np.random.default_rng(DEFAULT_SEED if seed is None else int(seed))

def spawn_seeds(seed: int, n: int) -> list[int]:
    gen = rng(seed)
    return [int(x) for x in gen.integers(1, 2**32 - 1, size=int(n), dtype=np.uint32)]
