import ast
import pickle
import struct

from ..opcodes import Opcodes


def generate(gen, node: ast.Constant) -> bytes:
    encoded = node.value.encode("utf-8")

    def _by_binstring() -> bytes:
        return Opcodes.BINSTRING + repr(node.value).encode("ascii") + b"\n"

    def _by_short_binunicode() -> bytes:
        return Opcodes.SHORT_BINUNICODE + bytes([len(encoded)]) + encoded

    def _by_binunicode() -> bytes:
        return Opcodes.BINUNICODE + struct.pack("<I", len(encoded)) + encoded

    def _by_string() -> bytes:
        # 交给 pickle 生成最规范的 payload
        payload = pickle.dumps(node.value, protocol=0)
        end = payload.index(b"\n", 1)
        return Opcodes.STRING + payload[1:end] + b"\n"

    bypass_map = {
        "V": lambda: _by_string(),
    }

    if all(ord(ch) < 128 for ch in node.value):
        # 仅当内容全部是 ASCII 构成时，才允许用 BINSTRING
        bypass_map["S"] = lambda: _by_binstring()

    if len(encoded) <= 0xFF:
        bypass_map["\\x8c"] = _by_short_binunicode
    bypass_map["X"] = _by_binunicode

    return gen.generate_with_firewall(bypass_map, node=node)
