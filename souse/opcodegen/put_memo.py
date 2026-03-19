import ast
from typing import Optional

from ..opcodes import Opcodes


def generate(gen, payload: bytes, node: Optional[ast.AST] = None) -> tuple[bytes, str]:
    memo_name = str(gen.ctx.memo_id)

    def _by_put() -> bytes:
        opcode = payload + Opcodes.PUT + f"{gen.ctx.memo_id}\n".encode("utf-8")
        gen.ctx.memo_id += 1
        return opcode

    def _by_memoize() -> bytes:
        opcode = payload + Opcodes.MEMOIZE
        gen.ctx.memo_id += 1
        return opcode

    return gen.generate_with_firewall(
        {
            Opcodes.PUT: _by_put,
            Opcodes.MEMOIZE: _by_memoize,
        },
        node=node,
    ), memo_name
