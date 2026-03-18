import ast
import struct

from ..opcodes import Opcodes


def generate(gen, node: ast.Constant) -> bytes:
    value = node.value

    def _by_int() -> bytes:
        return Opcodes.INT + f"{value}\n".encode()

    def _by_binint1() -> bytes:
        return Opcodes.BININT1 + bytes([value])

    def _by_binint2() -> bytes:
        return Opcodes.BININT2 + struct.pack("<H", value)

    def _by_binint() -> bytes:
        return Opcodes.BININT + struct.pack("<i", value)

    bypass_map = {
        Opcodes.INT: _by_int,
    }
    if -(2 ** 31) <= value <= (2 ** 31 - 1):
        bypass_map[Opcodes.BININT] = _by_binint
    if 0 <= value <= 0xFF:
        bypass_map[Opcodes.BININT1] = _by_binint1
    if 0 <= value <= 0xFFFF:
        bypass_map[Opcodes.BININT2] = _by_binint2

    choice = gen.check_firewall(list(bypass_map.keys()))
    return bypass_map[choice]()
