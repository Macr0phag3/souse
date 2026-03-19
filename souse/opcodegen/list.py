import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.List) -> bytes:
    def _by_list() -> bytes:
        return (
            Opcodes.MARK +
            b"".join([gen.emit(elt) for elt in node.elts]) +
            Opcodes.LIST
        )

    bypass_map = {
        Opcodes.LIST: _by_list,
    }
    return gen.generate_with_firewall(bypass_map, node=node)
