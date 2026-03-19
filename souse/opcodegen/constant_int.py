import ast
import pickle
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

    def _by_long1() -> bytes:
        encoded = pickle.encode_long(value)
        return Opcodes.LONG1 + bytes([len(encoded)]) + encoded

    def _by_long4() -> bytes:
        encoded = pickle.encode_long(value)
        return Opcodes.LONG4 + struct.pack("<I", len(encoded)) + encoded

    bypass_map = {
        "I": _by_int,
    }
    if -(2 ** 31) <= value <= (2 ** 31 - 1):
        bypass_map["J"] = _by_binint
    if 0 <= value <= 0xFF:
        bypass_map["K"] = _by_binint1
    if 0 <= value <= 0xFFFF:
        bypass_map["M"] = _by_binint2
    if len(pickle.encode_long(value)) < 0x100:
        bypass_map["\\x8a"] = _by_long1
    bypass_map["\\x8b"] = _by_long4

    return gen.generate_with_firewall(bypass_map, node=node)
