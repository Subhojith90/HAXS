#!/usr/bin/env python
from __future__ import annotations

import ast
import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR3_common import assert_execution_root_closed, require_isolated_interpreter, scan_runtime_tree, sha256_payload


def main() -> None:
    isolation = require_isolated_interpreter(ROOT)
    root_policy = assert_execution_root_closed(ROOT)
    tree = scan_runtime_tree(ROOT)
    python_files = [ROOT / relative for relative in tree["files"] if relative.endswith(".py")]
    failures = []
    for path in python_files:
        source = path.read_text(encoding="utf-8")
        try:
            ast.parse(source, filename=str(path))
            py_compile.compile(str(path), doraise=True)
        except Exception as error:
            failures.append({"path": str(path.relative_to(ROOT)), "error": repr(error)})
        conflict_markers = ["<" * 7, "=" * 7 + chr(10), ">" * 7]
        if any(marker in source for marker in conflict_markers):
            failures.append({"path": str(path.relative_to(ROOT)), "error": "merge-conflict marker"})
    if failures:
        raise SystemExit(json.dumps({"status": "FAIL", "failures": failures}, indent=2))
    print(json.dumps({"stage": "stage5c2gR3_1_static_gate", "status": "PASS", "python_files": len(python_files), "runtime_tree_sha256": sha256_payload(tree), "isolation": isolation, "execution_root_policy": root_policy}, indent=2))


if __name__ == "__main__": main()
