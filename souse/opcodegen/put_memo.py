import ast
from typing import Optional

from ..opcodes import Opcodes
from ..tools import put_color


def generate(gen, payload: bytes, node: Optional[ast.AST] = None) -> tuple[bytes, str]:
    memo_name = str(gen.ctx.memo_id)

    def _by_put() -> tuple[bytes, str]:
        opcode = payload + Opcodes.PUT + f"{gen.ctx.memo_id}\n".encode("utf-8")
        gen.ctx.memo_id += 1
        return opcode, memo_name

    def _by_memoize() -> tuple[bytes, str]:
        opcode = payload + Opcodes.MEMOIZE
        gen.ctx.memo_id += 1
        log_key = ("\\x94", ("p",))
        gen.ctx.bypass_choice_counts[log_key] = gen.ctx.bypass_choice_counts.get(log_key, 0) + 1
        return opcode, memo_name

    # 不能用 generate_with_firewall
    # 避免把内层 memo 写入的失败影响到整个 opcode 的生成
    put_blocked = Opcodes.PUT in gen.ctx.firewall_rules
    memoize_blocked = Opcodes.MEMOIZE in gen.ctx.firewall_rules

    if not put_blocked:
        return _by_put()

    if not memoize_blocked:
        return _by_memoize()

    gen.ctx._error(
        node,
        f"can NOT bypass: {put_color({'p': ['p'], '\\\\x94': ['\\\\x94']}, 'white')}",
    )
