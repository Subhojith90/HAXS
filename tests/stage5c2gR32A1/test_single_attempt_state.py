from __future__ import annotations

import json
import multiprocessing
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from stage5c2gR32A1_authorization import (
    STATE_PATH,
    reserve_attempt,
    terminalize_attempt,
)


def _reserve(root: str, queue: multiprocessing.Queue) -> None:
    candidate = {"candidate_sha256": "a" * 64}
    lock = {"receipt_id": "fixture-receipt"}
    try:
        record = reserve_attempt(candidate, lock, Path(root))
        queue.put(("PASS", record["attempt_id"]))
    except Exception as error:
        queue.put(("FAIL", type(error).__name__))


def test_multiprocess_race_allows_exactly_one_attempt(tmp_path: Path) -> None:
    queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = [
        multiprocessing.Process(target=_reserve, args=(str(tmp_path), queue))
        for _ in range(8)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0
    outcomes = [queue.get(timeout=2) for _ in processes]
    assert [outcome[0] for outcome in outcomes].count("PASS") == 1
    assert [outcome[0] for outcome in outcomes].count("FAIL") == 7
    state = json.loads(
        (tmp_path / STATE_PATH.relative_to(ROOT)).read_text(encoding="utf-8")
    )
    assert state["status"] == "RUNNING"


def test_terminal_state_is_immutable_and_second_attempt_is_rejected(
    tmp_path: Path,
) -> None:
    candidate = {"candidate_sha256": "a" * 64}
    lock = {"receipt_id": "fixture-receipt"}
    running = reserve_attempt(candidate, lock, tmp_path)
    terminal = terminalize_attempt(
        running,
        "FAILED",
        {"error": "frozen fixture failure"},
        tmp_path,
    )
    assert terminal["status"] == "FAILED"
    with pytest.raises(RuntimeError, match="already been attempted"):
        reserve_attempt(candidate, lock, tmp_path)


def test_stale_or_mutated_running_state_cannot_be_terminalized(
    tmp_path: Path,
) -> None:
    candidate = {"candidate_sha256": "a" * 64}
    lock = {"receipt_id": "fixture-receipt"}
    running = reserve_attempt(candidate, lock, tmp_path)
    state_path = tmp_path / STATE_PATH.relative_to(ROOT)
    mutated = json.loads(state_path.read_text(encoding="utf-8"))
    mutated["attempt_id"] = "attacker"
    state_path.write_text(json.dumps(mutated), encoding="utf-8")
    with pytest.raises(RuntimeError, match="changed"):
        terminalize_attempt(
            running,
            "FAILED",
            {"error": "must not overwrite stale state"},
            tmp_path,
        )
