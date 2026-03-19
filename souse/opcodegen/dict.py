import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.Dict) -> bytes:
    def _by_dict() -> bytes:
        return (
            Opcodes.MARK +
            b"".join([gen.emit(k) + gen.emit(v) for k, v in zip(node.keys, node.values) if k is not None]) +
            Opcodes.DICT
        )

    def _setitem_empty_dict() -> bytes:
        return (
            Opcodes.EMPTY_DICT
            + Opcodes.MARK
            + b"".join([gen.emit(k) + gen.emit(v) for k, v in zip(node.keys, node.values) if k is not None])
            + Opcodes.SETITEMS
        )

    bypass_map = {
        Opcodes.DICT: _by_dict,
    }
    if not node.keys:
        bypass_map[Opcodes.EMPTY_DICT] = lambda: Opcodes.EMPTY_DICT
    else:
        bypass_map[Opcodes.SETITEMS] = _setitem_empty_dict
    return gen.generate_with_firewall(bypass_map, node=node)
