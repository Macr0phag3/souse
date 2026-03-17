import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.Dict) -> bytes:
    def _by_dict() -> bytes:
        return (
            Opcodes.MARK +
            b"".join([gen.emit(k) + gen.emit(v) for k, v in zip(node.keys, node.values) if k is not None]) +
            Opcodes.DICT
        )

    bypass_map = {
        Opcodes.DICT: _by_dict,
    }
    choice = gen.check_firewall(list(bypass_map.keys()))
    return bypass_map[choice]()
