import ast
import pickle

from ..opcodes import Opcodes


def generate(gen, node: ast.Constant) -> bytes:
    def _by_binstring() -> bytes:
        return Opcodes.BINSTRING + repr(node.value).encode("ascii") + b"\n"

    def _by_string() -> bytes:
        # 交给 pickle 生成最规范的 payload
        payload = pickle.dumps(node.value, protocol=0)
        end = payload.index(b"\n", 1)
        return Opcodes.STRING + payload[1:end] + b"\n"

    bypass_map = {
        Opcodes.STRING: lambda: _by_string(),
    }

    if all(ord(ch) < 128 for ch in node.value):
        # 仅当内容全部是 ASCII 构成时，才允许用 BINSTRING
        bypass_map[Opcodes.BINSTRING] = lambda: _by_binstring()

    choice = gen.check_firewall(list(bypass_map.keys()))
    return bypass_map[choice]()
