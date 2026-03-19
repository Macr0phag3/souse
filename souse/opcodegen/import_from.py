import ast

from ..opcodes import Opcodes
from .put_memo import generate as put_memo


def generate(gen, node: ast.ImportFrom) -> bytes:
    # eg: from os import system
    # eg: from os import system as sys
    # eg: from os import system, popen
    def _by_global() -> bytes:
        ctx = gen.ctx
        opcode = b""
        for _name in node.names:
            name = _name.asname or _name.name
            global_opcode = Opcodes.GLOBAL + f'{node.module}\n{name}\n'.encode('utf-8')
            stored_opcode, memo_name = put_memo(gen, global_opcode, node=node)
            ctx.names[name] = [memo_name, node.module]
            opcode += stored_opcode
            as_suffix = f" as {_name.asname}" if _name.asname else ""
            ctx.converted_code.append(f"from {node.module} import {_name.name}{as_suffix}")
        return opcode

    bypass_map = {
        Opcodes.GLOBAL: _by_global,
    }
    return gen.generate_with_firewall(bypass_map, node=node)
