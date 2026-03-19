import sys
import ast
import pickletools
import tempfile
import subprocess
import os
from collections import Counter
from typing import Any, List, Optional

from .opcodegen import OpcodeGenerator
from .opcodes import Opcodes
from .tools import put_color
from .explain import explain as explain_opcodes


def _normalize_firewall_rules(firewall_rules: List[str]) -> set[bytes]:
    normalized = set()
    for key in firewall_rules:
        if key.startswith("\\x"):
            normalized.add(bytes([int(key[2:], 16)]))
            continue
        if key in {"I01", "I00"}:
            key += "\n"
        normalized.add(key.encode())
    return normalized


class Visitor(ast.NodeVisitor):
    def __init__(self, source_code: str, firewall_rules: List[str]) -> None:
        self.names = {}  # 变量记录
        self.memo_id = 0  # memo 的顶层 id
        self.firewall_rules = _normalize_firewall_rules(firewall_rules)
        self.source_code = source_code
        self.lazy_modules = {}  # import requests -> {'requests': 'requests'}

        self.final_opcode = b''
        self.pending_prefix_opcodes = []
        self.code = ""
        self.result = b""
        self.converted_code = []
        self.has_transformation = False
        self.bypass_choice_counts = {}
        self.gen = OpcodeGenerator(self)

    def souse(self) -> None:
        self.result = self.final_opcode + Opcodes.STOP
        for (label, rules), count in self.bypass_choice_counts.items():
            print(
                f"[*] choice {put_color(label, 'blue')} "
                f"to bypass rule: {put_color(list(rules), 'white')} "
                f"x{put_color(count, 'white')}"
            )

    def queue_prefix_opcode(self, opcode: bytes) -> None:
        self.pending_prefix_opcodes.append(opcode)

    def consume_prefix_opcodes(self) -> bytes:
        if not self.pending_prefix_opcodes:
            return b""
        opcode = b"".join(self.pending_prefix_opcodes)
        self.pending_prefix_opcodes.clear()
        return opcode

    def _error(self, node: Optional[ast.AST], msg: str) -> None:
        context = ""
        lineno = getattr(node, 'lineno', None)
        if lineno:
            start = lineno - 1
            end = getattr(node, 'end_lineno', None)
            end = end if end is not None else lineno
            lines = self.source_code.splitlines()
            if start < len(lines):
                context = f" in {put_color(lines[start:end], 'cyan')}"

        raise RuntimeError(put_color(msg, "red") + context)

    def generic_visit(self, node: ast.AST) -> None:
        # 只允许“容器/上下文”节点走默认遍历：
        # - Module/Expr：纯容器，不产生语义
        # - Load/Store/Del：仅上下文标记
        # 其它节点必须有显式 visit_XXX 实现，否则直接报错。
        # 注意：即便 visit_Assign 已实现，这里也不会处理 Assign，
        # 因为 NodeVisitor 会优先调用 visit_Assign，不走 generic_visit。
        if isinstance(node, (ast.Module, ast.Expr, ast.Load, ast.Store, ast.Del)):
            super().generic_visit(node)
        else:
            self._error(node, f"this struct is not supported yet: {node.__class__.__name__}")

    def check(self) -> str:
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8')
        try:
            tmp.write(
                'import pickle\n'
                f'print(pickle.loads({repr(self.result)}), end="")\n'
            )
            tmp.flush()
            tmp.close()
            output = subprocess.check_output([sys.executable, tmp.name], stderr=subprocess.STDOUT)
            return output.decode()
        finally:
            try:
                os.remove(tmp.name)
            except OSError:
                pass

    def optimize(self) -> bytes:
        def _normalize_memo_id(arg: Any) -> Any:
            try:
                return int(arg)
            except Exception:
                return arg

        put_ops = {"PUT", "BINPUT", "LONG_BINPUT"}
        get_ops = {"GET", "BINGET", "LONG_BINGET"}

        # 先做一次标准优化，统一字节流
        data = pickletools.optimize(self.result)
        # 按 opcode 级别解析，避免按换行切分破坏二进制数据
        ops = list(pickletools.genops(data))
        if not ops:
            return data

        # 用 genops 提供的位置计算每条 opcode 在字节流中的区间
        positions = [pos for _, _, pos in ops]
        ends = positions[1:] + [len(data)]

        # 统计每个 memo id 的 GET 使用次数
        get_counts = Counter(
            _normalize_memo_id(arg)
            for op, arg, _ in ops
            if op.name in get_ops
        )

        # 删除紧跟在 PUT 之后、且仅使用一次的 GET
        drop_indices = set()
        for i in range(len(ops) - 1):
            op, arg, _ = ops[i]
            next_op, next_arg, _ = ops[i + 1]

            if op.name not in put_ops or next_op.name not in get_ops:
                continue

            put_id = _normalize_memo_id(arg)
            get_id = _normalize_memo_id(next_arg)
            if (
                put_id == get_id and
                get_counts.get(get_id, 0) == 1
            ):
                drop_indices.add(i + 1)

        # 按区间重建字节流，再做一次标准优化
        rebuilt = b"".join(
            data[positions[i]:ends[i]]
            for i in range(len(ops))
            if i not in drop_indices
        )
        return pickletools.optimize(rebuilt)

    def explain(self, data: Optional[bytes] = None) -> str:
        data = self.result if data is None else data
        return explain_opcodes(data)

    def visit_Import(self, node: ast.Import) -> None:
        # eg: import os
        # eg: import os as o
        for _name in node.names:
            name = _name.name
            asname = _name.asname or name
            self.lazy_modules[asname] = name

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # eg: from os import system
        # eg: from os import system as sys
        # eg: from os import system, popen
        opcode = self.gen.emit(node)
        self.final_opcode += opcode

    def visit_Assign(self, node: ast.Assign) -> None:
        # 赋值
        start = node.lineno - 1
        end = getattr(node, 'end_lineno', None)
        end = end if end is not None else node.lineno
        self.code = put_color("\n".join(
            self.source_code.split('\n')[start:end]  # type: ignore
        ), "white")
        opcode = self.gen.emit(node)
        self.final_opcode += self.consume_prefix_opcodes() + opcode

    def _visit_expr_stmt(self, node: ast.AST) -> None:
        # 统一处理“表达式语句”
        def _generate_opcode():
            opcode = self.gen.emit(node)
            self.converted_code.append(self.gen.to_converted_code(node))
            self.final_opcode += self.consume_prefix_opcodes() + opcode

        start = node.lineno - 1
        end = getattr(node, 'end_lineno', None)
        end = end if end is not None else node.lineno
        self.code = put_color("\n".join(
            self.source_code.split('\n')[start:end]  # type: ignore
        ), "white")
        _generate_opcode()

    def visit_Call(self, node: ast.Call) -> None:
        # 函数调用（表达式语句）
        self._visit_expr_stmt(node)

    def visit_Name(self, node: ast.Name) -> None:
        # 单独使用变量名（表达式语句）
        self._visit_expr_stmt(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        # 下标访问（表达式语句）
        self._visit_expr_stmt(node)
