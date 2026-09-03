from __future__ import annotations

import sys
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A3_semantics import verify_junit_semantics

NODEIDS = [
    "tests/example/test_alpha.py::test_one",
    "tests/example/test_alpha.py::TestGroup::test_two[param]",
]


def write_junit(path: Path, nodeids: list[str], outcome: str | None = None) -> None:
    suite = Element(
        "testsuite", tests=str(len(nodeids)), failures=str(int(outcome == "failure")),
        errors=str(int(outcome == "error")), skipped=str(int(outcome == "skipped")),
    )
    for index, nodeid in enumerate(nodeids):
        parts = nodeid.split("::")
        module = parts[0][:-3].replace("/", ".")
        classname = ".".join([module, *parts[1:-1]]) if len(parts) > 2 else module
        case = SubElement(suite, "testcase", classname=classname, name=parts[-1])
        if index == 0 and outcome:
            SubElement(case, outcome)
    ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def test_exact_ordered_junit_ledger_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "exact.xml"
    write_junit(path, NODEIDS)
    assert verify_junit_semantics(path, NODEIDS)["tests"] == 2


@pytest.mark.parametrize("mutation", ["unrelated", "missing", "additional", "duplicate", "reordered"])
def test_wrong_identity_order_or_multiplicity_fails_closed(tmp_path: Path, mutation: str) -> None:
    observed = list(NODEIDS)
    if mutation == "unrelated": observed = ["tests/forged.py::test_x", "tests/forged.py::test_y"]
    elif mutation == "missing": observed.pop()
    elif mutation == "additional": observed.append("tests/example/test_alpha.py::test_three")
    elif mutation == "duplicate": observed[1] = observed[0]
    elif mutation == "reordered": observed.reverse()
    path = tmp_path / f"{mutation}.xml"
    write_junit(path, observed)
    with pytest.raises(RuntimeError):
        verify_junit_semantics(path, NODEIDS)


@pytest.mark.parametrize("outcome", ["skipped", "failure", "error"])
def test_nonpassing_testcase_fails_closed(tmp_path: Path, outcome: str) -> None:
    path = tmp_path / f"{outcome}.xml"
    write_junit(path, NODEIDS, outcome)
    with pytest.raises(RuntimeError):
        verify_junit_semantics(path, NODEIDS)
