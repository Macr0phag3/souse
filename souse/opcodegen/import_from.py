import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.ImportFrom) -> bytes:
    # eg: from os import system
    # eg: from os import system as sys
    # eg: from os import system, popen
    def _by_global() -> bytes:
        ctx = gen.ctx
        opcode = b""
        for _name in node.names:
            name = _name.asname or _name.name
            ctx.names[name] = [str(ctx.memo_id), node.module]
            opcode += Opcodes.GLOBAL + f'{node.module}\n{name}\n'.encode('utf-8') + Opcodes.PUT + f'{ctx.memo_id}\n'.encode('utf-8')
            as_suffix = f" as {_name.asname}" if _name.asname else ""
            ctx.converted_code.append(f"from {node.module} import {_name.name}{as_suffix}")
            ctx.memo_id += 1
        return opcode

    bypass_map = {
        Opcodes.GLOBAL: _by_global,
    }
    choice = gen.check_firewall(list(bypass_map.keys()), node=node)
    return bypass_map[choice]()
