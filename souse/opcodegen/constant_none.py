import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.Constant) -> bytes:
    bypass_map = {
        Opcodes.NONE: lambda: Opcodes.NONE,
    }
    return gen.generate_with_firewall(bypass_map, node=node)
