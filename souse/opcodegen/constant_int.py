import ast
import struct

from ..opcodes import Opcodes


def generate(gen, node: ast.Constant) -> bytes:
    def _by_int() -> bytes:
        return Opcodes.INT + f"{node.value}\n".encode()

    def _by_binint() -> bytes:
        return Opcodes.BININT + struct.pack("<i", node.value)

    bypass_map = {
        Opcodes.INT: _by_int,
        Opcodes.BININT: _by_binint,
    }
    choice = gen.check_firewall(list(bypass_map.keys()))
    return bypass_map[choice]()
