import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.Tuple) -> bytes:
    def _by_tuple() -> bytes:
        return (
            Opcodes.MARK +
            b"".join([gen.emit(elt) for elt in node.elts]) +
            Opcodes.TUPLE
        )

    def _by_tuple1() -> bytes:
        return gen.emit(node.elts[0]) + Opcodes.TUPLE1

    def _by_tuple2() -> bytes:
        return gen.emit(node.elts[0]) + gen.emit(node.elts[1]) + Opcodes.TUPLE2

    def _by_tuple3() -> bytes:
        return (
            gen.emit(node.elts[0])
            + gen.emit(node.elts[1])
            + gen.emit(node.elts[2])
            + Opcodes.TUPLE3
        )

    bypass_map = {
        Opcodes.TUPLE: _by_tuple,
    }

    if not node.elts:
        bypass_map[Opcodes.EMPTY_TUPLE] = lambda: Opcodes.EMPTY_TUPLE
    elif len(node.elts) == 1:
        bypass_map[Opcodes.TUPLE1] = _by_tuple1
    elif len(node.elts) == 2:
        bypass_map[Opcodes.TUPLE2] = _by_tuple2
    elif len(node.elts) == 3:
        bypass_map[Opcodes.TUPLE3] = _by_tuple3

    return gen.generate_with_firewall(bypass_map, node=node)
