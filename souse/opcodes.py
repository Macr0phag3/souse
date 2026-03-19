import ast
import copy
import pickletools
from typing import Any, Callable, Dict, Iterable, Optional

from .tools import put_color


class Opcodes:
    # 基础类型
    INT = b'I'
    LONG = b'L'
    BININT = b'J'
    BININT1 = b'K'
    BININT2 = b'M'
    LONG1 = b'\x8a'
    LONG4 = b'\x8b'
    FLOAT = b'F'
    BINFLOAT = b'G'
    STRING = b'V'
    BINSTRING = b'S'
    BINUNICODE = b'X'
    SHORT_BINUNICODE = b'\x8c'
    NONE = b'N'
    TRUE = b'I01\n'
    BINTRUE = b'\x88'
    FALSE = b'I00\n'
    BINFALSE = b'\x89'

    # 集合类型
    MARK = b'('
    EMPTY_LIST = b']'
    APPEND = b'a'
    APPENDS = b'e'
    LIST = b'l'
    EMPTY_TUPLE = b')'
    TUPLE = b't'
    TUPLE1 = b'\x85'
    TUPLE2 = b'\x86'
    TUPLE3 = b'\x87'
    DICT = b'd'
    EMPTY_SET = b'\x8f'
    ADDITEMS = b'\x90'

    # 操作类 opcode
    REDUCE = b'R'
    OBJ = b'o'
    INST = b'i'
    GLOBAL = b'c'
    STACK_GLOBAL = b'\x93'
    PUT = b'p'
    MEMOIZE = b'\x94'
    GET = b'g'
    STOP = b'.'

    # 字典 / 属性相关 opcode
    SETITEM = b's'
    SETITEMS = b'u'
    BUILD = b'b'
    EMPTY_DICT = b'}'
    NEWOBJ = b'\x81'
    NEWOBJ_EX = b'\x92'

def _load_generate(module_name: str, func_name: str = "generate") -> Callable[..., bytes]:
    module_name = f"{__package__}.opcodegen.{module_name}"
    module = __import__(module_name, fromlist=[func_name])
    return getattr(module, func_name)


def generate_constant(gen, node: ast.Constant) -> bytes:
    value = node.value

    if value is True or value is False:
        return _load_generate("constant_bool")(gen, node)
    if value is None:
        return _load_generate("constant_none")(gen, node)

    if isinstance(value, str):
        return _load_generate("string")(gen, node)
    if isinstance(value, int):
        return _load_generate("constant_int")(gen, node)
    if isinstance(value, float):
        return _load_generate("constant_float")(gen, node)

    gen.ctx._error(node, f"this basic type is not supported yet: {value} ({type(value)})")

class OpcodeGenerator:
    HANDLERS = {
        ast.Constant: generate_constant,
        **{
            node_type: _load_generate(module_name)
            for node_type, module_name in (
                (ast.Assign, "assign"),
                (ast.List, "list"),
                (ast.Set, "set"),
                (ast.Tuple, "tuple"),
                (ast.Dict, "dict"),
                (ast.ImportFrom, "import_from"),
                (ast.Name, "name"),
                (ast.Call, "call"),
                (ast.Attribute, "attribute"),
                (ast.Subscript, "subscript"),
                (ast.Slice, "slice"),
                (ast.UnaryOp, "unary"),
            )
        },
    }

    _ROLLBACK_FIELDS = (
        "names",
        "memo_id",
        "lazy_modules",
        "final_opcode",
        "pending_prefix_opcodes",
        "code",
        "result",
        "converted_code",
        "has_transformation",
    )

    def __init__(self, ctx: Any) -> None:
        self.ctx = ctx

    def _restore_ctx(self, snapshot: Dict[str, Any]) -> None:
        for field, value in snapshot.items():
            setattr(self.ctx, field, value)

    def _split_opcodes(self, data: bytes) -> Iterable[bytes]:
        """
        把一整段 pickle opcode 字节流按单条 opcode 切开
        """

        # 这里经常拿到的是中间 payload
        # 而不是完整 pickle 所以要临时补一个 STOP
        appended_stop = not data.endswith(Opcodes.STOP)
        parse_data = data if not appended_stop else data + Opcodes.STOP

        positions = [pos for _, _, pos in pickletools.genops(parse_data)]
        positions.append(len(parse_data))

        chunks = []
        for start, end in zip(positions, positions[1:]):
            raw = parse_data[start:end]
            if appended_stop and raw == Opcodes.STOP:
                continue
            chunks.append(raw)
        return chunks

    def _get_blocked_rules(self, data: bytes) -> list[str]:
        """
        获取被防火墙拦截的 opcode 列表
        """
        blocked = []
        for raw in self._split_opcodes(data):
            key = raw if raw in {Opcodes.TRUE, Opcodes.FALSE} else raw[:1]
            if key in self.ctx.firewall_rules:
                try:
                    blocked.append(key.decode().strip())
                except UnicodeDecodeError:
                    blocked.append(f"\\x{key[0]:02x}")
        return list(dict.fromkeys(blocked))

    def emit(self, node: ast.AST) -> bytes:
        """
        生成当前 AST 节点的最终 payload
        同时负责最终验收
        """
        handler = self.HANDLERS.get(type(node))
        if handler is None:
            self.ctx._error(node, f"this struct is not supported yet: {node.__class__.__name__}")

        prefix_count = len(self.ctx.pending_prefix_opcodes)
        payload = handler(self, node)
        # 某些 handler 会在生成当前 payload 的同时追加前缀 opcode
        # 比如 `getattr(a, "b")`
        # 会先补 `from builtins import getattr` 的前缀 opcode
        # 最终 opcode 等价于
        # from builtins import getattr
        # getattr(a, "b")
        prefix_opcode = b"".join(self.ctx.pending_prefix_opcodes[prefix_count:])

        # 防火墙校验要覆盖最终会一起落到结果里的完整 opcode 序列
        blocked_opcodes = self._get_blocked_rules(prefix_opcode + payload)
        if blocked_opcodes:
            self.ctx._error(node, f"can NOT bypass: {put_color(blocked_opcodes, 'white')}")
        return payload

    def generate_with_firewall(
        self,
        bypass_map: Dict[bytes | str, Callable[[], bytes | None]],
        node: Optional[ast.AST] = None,
    ) -> bytes:
        """
        负责选择绕过方案，
        尝试所有 bypass 选项
        直到找到一个不被防火墙拦截的写法
        """
        def display_label(label: bytes | str) -> str:
            if isinstance(label, str):
                return label
            try:
                return label.decode().strip()
            except UnicodeDecodeError:
                return f"\\x{label[0]:02x}"

        rejected_by_firewall = {}

        for label, producer in bypass_map.items():
            # 每次试跑前先保存关键变量的现场，失败后要回滚
            snapshot = {
                field: copy.deepcopy(getattr(self.ctx, field))
                for field in self._ROLLBACK_FIELDS
            }
            prefix_count = len(self.ctx.pending_prefix_opcodes)

            # 真正执行当前候选写法并拿到生成出的 payload
            payload = producer()
            if payload is None:
                self._restore_ctx(snapshot)
                continue

            blocked_opcodes = self._get_blocked_rules(
                b"".join(self.ctx.pending_prefix_opcodes[prefix_count:]) + payload
            )
            if blocked_opcodes:
                # 被防火墙 ban 了，记录下来
                # 恢复现场后继续下一个
                rejected_by_firewall[display_label(label)] = blocked_opcodes
                self._restore_ctx(snapshot)
                continue

            if rejected_by_firewall:
                # 前面有候选失败过时 打印最终选中的绕过方案
                merged_rules = []
                for rules in rejected_by_firewall.values():
                    merged_rules.extend(rules)
                merged_rules = list(dict.fromkeys(merged_rules))
                log_key = (display_label(label), tuple(merged_rules))
                self.ctx.bypass_choice_counts[log_key] = self.ctx.bypass_choice_counts.get(log_key, 0) + 1

            return payload

        if rejected_by_firewall:
            lines = ["can NOT bypass"]
            for label, rules in rejected_by_firewall.items():
                lines.append(f"- {put_color(', '.join(rules), 'yellow')} blocked {put_color(label, 'white')}")
            self.ctx._error(
                node,
                "\n".join(lines),
            )

        self.ctx._error(
            node,
            f"NO bypass is applicable: {put_color([display_label(label) for label in bypass_map], 'white')}",
        )

    def to_converted_code(self, node: ast.AST, is_assignment: bool = False) -> str:
        """
        把 AST 节点转换成 Python 代码字符串
        """

        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id in self.ctx.lazy_modules:
                return node.attr
            return f'getattr({self.to_converted_code(node.value)}, "{node.attr}")'

        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Tuple):
            return f"({', '.join(self.to_converted_code(elt) for elt in node.elts)})"

        if isinstance(node, ast.List):
            return f"[{', '.join(self.to_converted_code(elt) for elt in node.elts)}]"

        if isinstance(node, ast.Set):
            return f"{{{', '.join(self.to_converted_code(elt) for elt in node.elts)}}}"

        if isinstance(node, ast.Dict):
            items = []
            for key, value in zip(node.keys, node.values):
                if key is None:
                    continue
                items.append(
                    f"{self.to_converted_code(key)}: {self.to_converted_code(value)}"
                )
            return f"{{{', '.join(items)}}}"

        if isinstance(node, ast.Subscript):
            slice_node = node.slice
            if isinstance(slice_node, ast.Index):
                slice_node = getattr(slice_node, "value")

            if is_assignment:
                return (
                    f"{self.to_converted_code(node.value)}"
                    f"[{self.to_converted_code(slice_node)}]"
                )
            return (
                f'getattr({self.to_converted_code(node.value)}, "__getitem__")'
                f"({self.to_converted_code(slice_node)})"
            )

        if isinstance(node, ast.Call):
            args = ", ".join(self.to_converted_code(arg) for arg in node.args)
            return f"{self.to_converted_code(node.func)}({args})"

        if isinstance(node, ast.Slice):
            lower = self.to_converted_code(node.lower) if node.lower else "None"
            upper = self.to_converted_code(node.upper) if node.upper else "None"
            step = self.to_converted_code(node.step) if node.step else "None"
            return f"slice({lower}, {upper}, {step})"

        if isinstance(node, ast.Constant):
            return repr(node.value)

        if isinstance(node, ast.UnaryOp):
            operand = self.to_converted_code(node.operand)
            if isinstance(node.op, ast.USub):
                return f"-{operand}"
            if isinstance(node.op, ast.UAdd):
                return f"+{operand}"
            if isinstance(node.op, ast.Not):
                return f"not {operand}"
            if isinstance(node.op, ast.Invert):
                return f"~{operand}"

        return ast.unparse(node)


__all__ = [
    "Opcodes",
    "OpcodeGenerator",
    "generate_constant",
]
