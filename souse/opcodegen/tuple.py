import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.Tuple) -> bytes:
    def _by_tuple() -> bytes:
        return (
            Opcodes.MARK +
            b"".join([gen.emit(elt) for elt in node.elts]) +
            Opcodes.TUPLE
        )

    bypass_map = {
        "t": _by_tuple,
    }
    return gen.generate_with_firewall(bypass_map, node=node)
