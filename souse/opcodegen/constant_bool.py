import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.Constant) -> bytes:
    if node.value is True:
        bypass_map = {
            "I01": lambda: Opcodes.TRUE,
            "\\x88": lambda: Opcodes.BINTRUE,
        }
    else:
        bypass_map = {
            "I00": lambda: Opcodes.FALSE,
            "\\x89": lambda: Opcodes.BINFALSE,
        }

    return gen.generate_with_firewall(bypass_map, node=node)
