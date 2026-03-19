import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.List) -> bytes:
    def _by_list() -> bytes:
        return (
            Opcodes.MARK +
            b"".join([gen.emit(elt) for elt in node.elts]) +
            Opcodes.LIST
        )

    def _append_empty_list() -> bytes:
        return (
            Opcodes.EMPTY_LIST
            + Opcodes.MARK
            + b"".join([gen.emit(elt) for elt in node.elts])
            + Opcodes.APPENDS
        )

    bypass_map = {
        Opcodes.LIST: _by_list,
    }
    if not node.elts:
        bypass_map[Opcodes.EMPTY_LIST] = lambda: Opcodes.EMPTY_LIST
    else:
        bypass_map[Opcodes.APPENDS] = _append_empty_list
    return gen.generate_with_firewall(bypass_map, node=node)
