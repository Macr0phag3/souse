import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.Constant) -> bytes:
    if node.value is True:
        bypass_map = {
            Opcodes.TRUE: lambda: Opcodes.TRUE,
            Opcodes.BINTRUE: lambda: Opcodes.BINTRUE,
        }
    else:
        bypass_map = {
            Opcodes.FALSE: lambda: Opcodes.FALSE,
            Opcodes.BINFALSE: lambda: Opcodes.BINFALSE,
        }

    return gen.generate_with_firewall(bypass_map, node=node)
