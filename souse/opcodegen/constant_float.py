import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.Constant) -> bytes:
    def _by_float() -> bytes:
        return Opcodes.FLOAT + f"{node.value}\n".encode()

    bypass_map = {
        Opcodes.FLOAT: _by_float,
    }
    choice = gen.check_firewall(list(bypass_map.keys()))
    return bypass_map[choice]()
