import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.Constant) -> bytes:
    bypass_map = {
        Opcodes.NONE: lambda: Opcodes.NONE,
    }
    choice = gen.check_firewall(list(bypass_map.keys()))
    return bypass_map[choice]()
