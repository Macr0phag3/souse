import ast

import pytest

from souse.api import API
from souse.opcodes import Opcodes
from souse.visitor import Visitor


def test_firewall_rejects_nested_opcode_in_real_payload():
    with pytest.raises(RuntimeError, match="can NOT bypass"):
        API(
            'getattr("abc", "upper")',
            firewall_rules=["c", "\\x93"],
            optimized=False,
            transfer="",
        ).generate()


def test_generate_with_firewall_propagates_candidate_error():
    visitor = Visitor("None", ["c", "\\x93"])

    def _unsafe() -> bytes:
        return visitor.gen.emit(ast.Name(id="getattr", ctx=ast.Load()))

    with pytest.raises(RuntimeError, match="can NOT bypass"):
        visitor.gen.generate_with_firewall(
            {
                "unsafe": _unsafe,
                "safe": lambda: Opcodes.NONE,
            }
        )
    assert visitor.pending_prefix_opcodes == []
    assert visitor.names == {}
