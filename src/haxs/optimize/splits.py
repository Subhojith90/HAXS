from __future__ import annotations
from haxs.utils.rng import spawn_seeds

def train_test_seeds(seed: int, n_train: int, n_test: int) -> dict[str, list[int]]:
    seeds = spawn_seeds(seed, int(n_train) + int(n_test))
    train = seeds[:int(n_train)]
    test = seeds[int(n_train):]
    if set(train) & set(test):
        raise RuntimeError("train/test split has overlapping seeds")
    return {"train": train, "test": test}
