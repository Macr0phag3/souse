import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.Set) -> bytes:
    def _by_set() -> bytes:
        # PVM Protocol 4
        return (
            Opcodes.EMPTY_SET + b"(" +
            b"".join([gen.emit(elt) for elt in node.elts]) +
            Opcodes.ADDITEMS
        )

    bypass_map = {
        Opcodes.ADDITEMS: _by_set,
    }
    choice = gen.check_firewall(list(bypass_map.keys()))
    return bypass_map[choice]()
