import ast
import json
from pathlib import Path

import pytest

from souse.api import API


CASE_DIR = Path("souse/cases")


def _load_firewall_rules(source: str) -> dict:
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("# firewall:"):
            return json.loads(stripped[len("# firewall:"):].strip())
    return {}


def _load_expected_bytes(source: str) -> bytes:
    for line in reversed(source.splitlines()):
        stripped = line.strip()
        if stripped.startswith("# b") or stripped.startswith('# b"'):
            return ast.literal_eval(stripped[2:].strip())
    raise AssertionError("missing expected bytes comment")


SUCCESS_CASES = [
    path
    for path in sorted(CASE_DIR.glob("*.py"))
    if not path.name.startswith("test_")
]


@pytest.mark.parametrize("path", SUCCESS_CASES, ids=lambda path: path.name)
def test_case_output_matches_expected_answer(path: Path):
    source = path.read_text()
    result = API(
        source,
        firewall_rules=_load_firewall_rules(source),
        optimized=False,
        transfer="",
    ).generate()
    assert result == _load_expected_bytes(source)
