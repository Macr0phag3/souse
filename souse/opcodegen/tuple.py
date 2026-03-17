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
        Opcodes.TUPLE: _by_tuple,
    }
    choice = gen.check_firewall(list(bypass_map.keys()))
    return bypass_map[choice]()
