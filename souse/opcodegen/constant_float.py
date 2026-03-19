import ast
import struct

from ..opcodes import Opcodes


def generate(gen, node: ast.Constant) -> bytes:
    def _by_float() -> bytes:
        return Opcodes.FLOAT + f"{node.value}\n".encode()

    def _by_binfloat() -> bytes:
        return Opcodes.BINFLOAT + struct.pack(">d", node.value)

    bypass_map = {
        Opcodes.FLOAT: _by_float,
        Opcodes.BINFLOAT: _by_binfloat,
    }
    return gen.generate_with_firewall(bypass_map, node=node)
