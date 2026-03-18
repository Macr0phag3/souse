import json
import pickletools
from pathlib import Path

from souse.api import API
from souse.explain import EXPLAINED_OPS, explain
from souse.opcodes import Opcodes


def _load_firewall_rules(source: str) -> dict:
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("# firewall:"):
            return json.loads(stripped[len("# firewall:"):].strip())
    return {}


def _opcode_name_from_bytes(value: bytes) -> str:
    return pickletools.code2op[value[:1].decode("latin1")].name


def _has_expected_error(source: str) -> bool:
    return any(line.strip().startswith("# error:") for line in source.splitlines())


def test_opcode_constants_have_explain_coverage():
    opcode_names = {
        _opcode_name_from_bytes(value)
        for name, value in vars(Opcodes).items()
        if name.isupper() and isinstance(value, bytes) and value
    }

    missing = sorted(opcode_names - EXPLAINED_OPS)
    assert not missing, f"missing explain coverage for opcode constants: {missing}"


def test_case_outputs_have_explain_coverage():
    emitted_ops = set()

    for path in sorted(Path("souse/cases").glob("*.py")):
        source = path.read_text()
        if path.name.startswith("test_") or _has_expected_error(source):
            continue
        visitor = API(
            source,
            firewall_rules=_load_firewall_rules(source),
            optimized=False,
            transfer="",
        )._generate()

        op_names = {op.name for op, _, _ in pickletools.genops(visitor.result)}
        emitted_ops.update(op_names)

        explanation = explain(visitor.result)
        assert "no rule" not in explanation, f"{path} contains unexplained opcodes"

    missing = sorted(emitted_ops - EXPLAINED_OPS)
    assert not missing, f"missing explain coverage for emitted opcodes: {missing}"
