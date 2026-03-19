import ast
import pickletools
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple

from .tools import put_color


class _RenderableValue:
    def render(self) -> str:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.render()


@dataclass
class _LiteralValue(_RenderableValue):
    text: str

    def render(self) -> str:
        return self.text


@dataclass
class _TupleValue(_RenderableValue):
    items: List[Any]

    def render(self) -> str:
        rendered = ", ".join(str(item) for item in self.items)
        if len(self.items) == 1:
            rendered += ","
        return f"({rendered})"


@dataclass
class _ListValue(_RenderableValue):
    items: List[Any] = field(default_factory=list)

    def append(self, item: Any) -> None:
        self.items.append(item)

    def extend(self, items: List[Any]) -> None:
        self.items.extend(items)

    def render(self) -> str:
        return "[" + ", ".join(str(item) for item in self.items) + "]"


@dataclass
class _DictValue(_RenderableValue):
    items: List[Tuple[Any, Any]] = field(default_factory=list)

    def set_item(self, key: Any, val: Any) -> None:
        key_text = str(key)
        for idx, (existing_key, _existing_val) in enumerate(self.items):
            if str(existing_key) == key_text:
                self.items[idx] = (key, val)
                return
        self.items.append((key, val))

    def update(self, pairs: List[Tuple[Any, Any]]) -> None:
        for key, val in pairs:
            self.set_item(key, val)

    def render(self) -> str:
        return "{" + ", ".join(f"{key}: {val}" for key, val in self.items) + "}"


@dataclass
class _SetValue(_RenderableValue):
    items: List[Any] = field(default_factory=list)

    def update(self, items: List[Any]) -> None:
        existing = {str(item) for item in self.items}
        for item in items:
            text = str(item)
            if text not in existing:
                self.items.append(item)
                existing.add(text)

    def render(self) -> str:
        if not self.items:
            return "set()"
        return "{" + ", ".join(str(item) for item in self.items) + "}"


_INT_OPS = {"BININT", "BININT1", "BININT2", "INT", "LONG", "LONG1", "LONG4"}
_FLOAT_OPS = {"FLOAT", "BINFLOAT"}
_STRING_OPS = {"BINUNICODE", "SHORT_BINUNICODE", "UNICODE", "STRING"}
_BYTES_OPS = {"BINBYTES", "SHORT_BINBYTES", "BYTEARRAY8", "BINBYTES8"}

_LITERAL_PUSHES: Dict[str, Tuple[str, str]] = {
    "NONE": ("None", "压入 None"),
    "NEWTRUE": ("True", "压入布尔值 True"),
    "BINTRUE": ("True", "压入布尔值 True"),
    "NEWFALSE": ("False", "压入布尔值 False"),
    "BINFALSE": ("False", "压入布尔值 False"),
}

_EMPTY_FACTORIES: Dict[str, Tuple[Callable[[], Any], str]] = {
    "EMPTY_LIST": (_ListValue, "构造空 list"),
    "EMPTY_TUPLE": (lambda: _TupleValue([]), "构造空 tuple"),
    "EMPTY_DICT": (_DictValue, "构造空 dict"),
    "EMPTY_SET": (_SetValue, "构造空 set"),
}

_FIXED_TUPLES: Dict[str, Tuple[int, str]] = {
    "TUPLE1": (1, "构造 1 元素 tuple"),
    "TUPLE2": (2, "构造 2 元素 tuple"),
    "TUPLE3": (3, "构造 3 元素 tuple"),
}

_SPECIAL_HANDLERS = {
    "PROTO": "_handle_proto",
    "FRAME": "_handle_frame",
    "MARK": "_handle_mark",
    "STOP": "_handle_stop",
    "GLOBAL": "_handle_global",
    "STACK_GLOBAL": "_handle_stack_global",
    "TUPLE": "_handle_marked_tuple",
    "LIST": "_handle_marked_list",
    "DICT": "_handle_marked_dict",
    "APPEND": "_handle_append",
    "APPENDS": "_handle_appends",
    "ADDITEMS": "_handle_additems",
    "SETITEM": "_handle_setitem",
    "SETITEMS": "_handle_setitems",
    "PUT": "_handle_put",
    "BINPUT": "_handle_put",
    "LONG_BINPUT": "_handle_put",
    "GET": "_handle_get",
    "BINGET": "_handle_get",
    "LONG_BINGET": "_handle_get",
    "MEMOIZE": "_handle_memoize",
    "POP": "_handle_pop",
    "POP_MARK": "_handle_pop_mark",
    "REDUCE": "_handle_reduce",
    "BUILD": "_handle_build",
    "NEWOBJ": "_handle_newobj",
    "NEWOBJ_EX": "_handle_newobj_ex",
    "OBJ": "_handle_obj",
    "INST": "_handle_inst",
}

EXPLAINED_OPS = (
    set(_INT_OPS)
    | set(_FLOAT_OPS)
    | set(_STRING_OPS)
    | set(_BYTES_OPS)
    | set(_LITERAL_PUSHES)
    | set(_EMPTY_FACTORIES)
    | set(_FIXED_TUPLES)
    | set(_SPECIAL_HANDLERS)
)


class _Explainer:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.ops = list(pickletools.genops(data))
        self.total = len(self.ops)
        self.positions = [pos for _, _, pos in self.ops]
        self.ends = self.positions[1:] + [len(data)]

        self.marker = object()
        self.stack: List[Any] = []
        self.memo: Dict[Any, Any] = {}
        self.memo_next_id = 0
        self.max_stack = 0

    def render(self) -> str:
        lines = ["", ""]
        for idx, (op, arg, _pos) in enumerate(self.ops):
            lines.extend(self._render_operation(idx, op.name, arg))

        lines[1] = self._summary_line()
        return "\n".join(lines)

    def _render_operation(self, idx: int, op_name: str, arg: Any) -> List[str]:
        before_items = self._stack_items(self.stack)
        meaning = self._apply(op_name, arg)

        after_items = self._stack_items(self.stack)
        diff_idx = self._diff_start(before_items, after_items)
        raw = self.data[self.positions[idx]:self.ends[idx]]

        lines = [
            self._format_operation_line(op_name, arg, raw),
            f"    opcode: {self._opcode_trace(idx)}",
            f"    meaning: {put_color(meaning, 'white', bold=True)}",
            f"    stack-before: {self._format_stack(before_items, diff_idx)}",
            f"    stack-after:  {self._format_stack(after_items, diff_idx)}",
        ]
        if op_name == "STOP":
            final_value = after_items[-1] if after_items else "<empty>"
            lines.append(f"    final-value: {put_color(final_value, 'green')}")
        return lines

    def _apply(self, op_name: str, arg: Any) -> str:
        literal_spec = _LITERAL_PUSHES.get(op_name)
        if literal_spec is not None:
            return self._push_literal(*literal_spec)

        if op_name in _INT_OPS:
            return self._push_arg_text(arg, "压入整数 {}")
        if op_name in _FLOAT_OPS:
            return self._push_arg_text(arg, "压入浮点数 {}")
        if op_name in _STRING_OPS:
            return self._push_repr(arg, "压入字符串")
        if op_name in _BYTES_OPS:
            return self._push_repr(arg, "压入字节串")

        empty_spec = _EMPTY_FACTORIES.get(op_name)
        if empty_spec is not None:
            factory, meaning = empty_spec
            self._push(factory())
            return meaning

        fixed_tuple_spec = _FIXED_TUPLES.get(op_name)
        if fixed_tuple_spec is not None:
            size, meaning = fixed_tuple_spec
            self._push_fixed_tuple(size)
            return meaning

        handler_name = _SPECIAL_HANDLERS.get(op_name)
        if handler_name is None:
            return "no rule"
        return getattr(self, handler_name)(arg)

    def _stack_items(self, items: List[Any]) -> List[str]:
        rendered = []
        for item in items:
            if item is self.marker:
                rendered.append("<MARK>")
            else:
                rendered.append(str(item))
        return rendered

    def _missing_value(self) -> _LiteralValue:
        return _LiteralValue("<missing>")

    def _pairs_from_items(self, items: List[Any]) -> List[Tuple[Any, Any]]:
        pairs = []
        for i in range(0, len(items), 2):
            key = items[i]
            val = items[i + 1] if i + 1 < len(items) else self._missing_value()
            pairs.append((key, val))
        return pairs

    def _diff_start(self, before: List[str], after: List[str]) -> int:
        n = min(len(before), len(after))
        i = 0
        while i < n and before[i] == after[i]:
            i += 1
        return i

    def _format_stack(self, items: List[str], diff_idx: int) -> str:
        if not items:
            return "[]"

        rendered = []
        for i, item in enumerate(items):
            if i >= diff_idx:
                rendered.append(put_color(item, "yellow"))
            else:
                rendered.append(item)
        return "[" + ", ".join(rendered) + "]"

    def _push(self, val: Any) -> None:
        self.stack.append(val)
        self.max_stack = max(self.max_stack, len(self.stack))

    def _push_literal(self, literal: str, meaning: str) -> str:
        self._push(_LiteralValue(literal))
        return meaning

    def _push_arg_text(self, arg: Any, meaning_template: str) -> str:
        if isinstance(arg, bool):
            self._push(_LiteralValue(str(arg)))
            return f"压入布尔值 {arg}"
        self._push(_LiteralValue(str(arg)))
        return meaning_template.format(arg)

    def _push_repr(self, arg: Any, meaning: str) -> str:
        self._push(_LiteralValue(repr(arg)))
        return meaning

    def _push_fixed_tuple(self, size: int) -> None:
        items = [self._pop() for _ in range(size)]
        items.reverse()
        self._push(_TupleValue(items))

    def _push_marker(self) -> None:
        self.stack.append(self.marker)
        self.max_stack = max(self.max_stack, len(self.stack))

    def _pop(self) -> Any:
        if not self.stack:
            return _LiteralValue("<empty>")
        return self.stack.pop()

    def _pop_marked(self) -> List[Any]:
        if self.marker not in self.stack:
            return []

        items = []
        while self.stack and self.stack[-1] is not self.marker:
            items.append(self.stack.pop())
        if self.stack and self.stack[-1] is self.marker:
            self.stack.pop()
        items.reverse()
        return items

    def _memo_id(self, arg: Any) -> Any:
        try:
            return int(arg)
        except Exception:
            return arg

    def _join_items(self, items: List[Any]) -> str:
        return ", ".join(str(item) for item in items)

    def _tuple_items(self, value: Any) -> List[Any] | None:
        if isinstance(value, _TupleValue):
            return value.items
        return None

    def _dict_items(self, value: Any) -> List[Tuple[Any, Any]] | None:
        if isinstance(value, _DictValue):
            return value.items
        return None

    def _is_none_literal(self, value: Any) -> bool:
        return isinstance(value, _LiteralValue) and value.text == "None"

    def _render_reduce_call(self, func: Any, args: Any) -> str:
        tuple_items = self._tuple_items(args)
        if tuple_items is None:
            return f"{func}({args})"
        return f"{func}({self._join_items(tuple_items)})"

    def _describe_reduce(self, func: Any, args: Any) -> str:
        return f"调用 {self._render_reduce_call(func, args)}"

    def _render_call(self, func: Any, args: Any, kwargs: Any = None) -> str:
        tuple_items = self._tuple_items(args)
        arg_parts = [str(item) for item in tuple_items] if tuple_items is not None else [str(args)]
        if tuple_items == []:
            arg_parts = []

        if kwargs is None:
            return f"{func}({', '.join(arg_parts)})"

        dict_items = self._dict_items(kwargs)
        if dict_items is None:
            arg_parts.append(f"**{kwargs}")
        else:
            arg_parts.extend(
                f"{self._format_attr_name(key)}={val}"
                for key, val in dict_items
            )
        return f"{func}({', '.join(arg_parts)})"

    def _format_attr_name(self, key: Any) -> str:
        if isinstance(key, _LiteralValue):
            try:
                parsed = ast.literal_eval(key.text)
            except Exception:
                return str(key)
            if isinstance(parsed, str):
                return parsed
        return str(key)

    def _describe_build(self, inst: Any, state: Any) -> str:
        tuple_items = self._tuple_items(state)
        if tuple_items is None or len(tuple_items) != 2:
            return f"对 {inst} 应用状态 {state}"

        slot_state, dict_state = tuple_items
        dict_items = self._dict_items(dict_state)
        if dict_items is None:
            return f"对 {inst} 应用状态 {state}"

        attr_parts = [f"{self._format_attr_name(key)} = {val}" for key, val in dict_items]
        if not self._is_none_literal(slot_state):
            attr_parts.insert(0, f"slotstate = {slot_state}")

        if not attr_parts:
            return f"对 {inst} 应用空状态"
        return f"给 {inst} 设置属性 {', '.join(attr_parts)}"

    def _format_arg(self, op_name: str, arg: Any) -> str:
        if arg is None:
            return ""
        if op_name in _STRING_OPS or op_name in _BYTES_OPS:
            return repr(arg)
        if op_name in {"GLOBAL", "INST"} and isinstance(arg, str):
            parts = arg.split(" ", 1)
            if len(parts) == 2:
                return f"{repr(parts[0])} {repr(parts[1])}"
            return repr(arg)
        return str(arg)

    def _format_opcode_literal(self, raw: bytes) -> str:
        if not raw:
            return put_color("?", "green")

        out = []
        for idx, byte in enumerate(raw):
            is_opcode = idx == 0
            if byte == 0x0A:
                text = "\\n"
            elif byte == 0x0D:
                text = "\\r"
            elif byte == 0x09:
                text = "\\t"
            elif byte == 0x5C:
                text = "\\\\"
            elif 32 <= byte <= 126:
                text = chr(byte)
            else:
                text = f"\\x{byte:02x}"

            color = "green" if is_opcode else "white"
            if not is_opcode and text in {"\\n", "\\r", "\\t"}:
                color = "gray"
            out.append(put_color(text, color))

        return "".join(out)

    def _format_opcode_trace_literal(self, raw: bytes, color: str) -> str:
        if not raw:
            return put_color("?", color)

        out = []
        for byte in raw:
            if byte == 0x0A:
                text = "\\n"
            elif byte == 0x0D:
                text = "\\r"
            elif byte == 0x09:
                text = "\\t"
            elif byte == 0x5C:
                text = "\\\\"
            elif 32 <= byte <= 126:
                text = chr(byte)
            else:
                text = f"\\x{byte:02x}"
            out.append(put_color(text, color))

        return "".join(out)

    def _format_operation_line(self, op_name: str, arg: Any, raw: bytes) -> str:
        op_line = (
            f"{put_color('[', 'gray')}"
            f"{self._format_opcode_literal(raw)}"
            f"{put_color(']', 'gray')}"
            f"{put_color(' ', 'gray')}{put_color(op_name, 'cyan')}"
        )
        arg_text = self._format_arg(op_name, arg)
        if arg_text:
            op_line += f"{put_color(' ', 'gray')}{put_color(arg_text, 'cyan')}"
        return op_line

    def _opcode_trace(self, idx: int) -> str:
        previous = "".join(
            self._format_opcode_trace_literal(
                self.data[self.positions[i]:self.ends[i]],
                "green",
            )
            for i in range(idx)
        )
        current = self._format_opcode_trace_literal(
            self.data[self.positions[idx]:self.ends[idx]],
            "yellow",
        )
        return previous + current

    def _summary_line(self) -> str:
        memo_count = len(self.memo)
        return (
            f"{put_color('[*] opcode summary', 'cyan')} "
            f"\n- total: {put_color(self.total, 'green')}, "
            f"max_stack: {put_color(self.max_stack, 'green')}, "
            f"memo: {put_color(memo_count, 'green')}"
            f"\n- explain:\n"
        )

    def _handle_proto(self, arg: Any) -> str:
        return f"使用 pickle 协议 {arg}"

    def _handle_frame(self, arg: Any) -> str:
        return f"frame size {arg}"

    def _handle_mark(self, _arg: Any) -> str:
        self._push_marker()
        return "压入 MARK"

    def _handle_stop(self, _arg: Any) -> str:
        return "停止反序列化"

    def _handle_global(self, arg: Any) -> str:
        if isinstance(arg, str) and " " in arg:
            module, name = arg.split(" ", 1)
            symbol = f"{module}.{name}"
            self._push(_LiteralValue(symbol))
            return f"从 {module} 导入 {name}"

        self._push(_LiteralValue(str(arg)))
        return f"导入全局对象 {arg}"

    def _handle_stack_global(self, _arg: Any) -> str:
        name = self._pop()
        module = self._pop()
        symbol = f"{module}.{name}"
        self._push(_LiteralValue(symbol))
        return f"从 {module} 导入 {name}"

    def _handle_marked_tuple(self, _arg: Any) -> str:
        self._push(_TupleValue(self._pop_marked()))
        return "构造 tuple"

    def _handle_marked_list(self, _arg: Any) -> str:
        self._push(_ListValue(self._pop_marked()))
        return "构造 list"

    def _handle_marked_dict(self, _arg: Any) -> str:
        self._push(_DictValue(self._pairs_from_items(self._pop_marked())))
        return "构造 dict"

    def _handle_append(self, _arg: Any) -> str:
        item = self._pop()
        lst = self._pop()
        if isinstance(lst, _ListValue):
            lst.append(item)
            self._push(lst)
        else:
            self._push(_LiteralValue(f"{lst} + [{item}]"))
        return "向 list 追加元素"

    def _handle_appends(self, _arg: Any) -> str:
        items = self._pop_marked()
        lst = self._pop()
        if isinstance(lst, _ListValue):
            lst.extend(items)
            self._push(lst)
        else:
            self._push(_LiteralValue(f"{lst} + [{self._join_items(items)}]"))
        return "向 list 批量追加元素"

    def _handle_additems(self, _arg: Any) -> str:
        items = self._pop_marked()
        st = self._pop()
        if isinstance(st, _SetValue):
            st.update(items)
            self._push(st)
        else:
            self._push(_LiteralValue(f"{st} | {{{self._join_items(items)}}}"))
        return "向 set 批量追加元素"

    def _handle_setitem(self, _arg: Any) -> str:
        val = self._pop()
        key = self._pop()
        dct = self._pop()
        if isinstance(dct, _DictValue):
            dct.set_item(key, val)
            self._push(dct)
        else:
            self._push(_LiteralValue(f"{dct}{{{key}: {val}}}"))
        return "向 dict 写入单个键值"

    def _handle_setitems(self, _arg: Any) -> str:
        items = self._pop_marked()
        dct = self._pop()
        if isinstance(dct, _DictValue):
            dct.update(self._pairs_from_items(items))
            self._push(dct)
        else:
            pairs = self._pairs_from_items(items)
            rendered = ", ".join(f"{key}: {val}" for key, val in pairs)
            self._push(_LiteralValue(f"{dct}{{{rendered}}}"))
        return "向 dict 批量写入键值"

    def _handle_put(self, arg: Any) -> str:
        memo_id = self._memo_id(arg)
        self.memo[memo_id] = self.stack[-1] if self.stack else "<empty>"
        return f"写入 memo[{memo_id}] = {self.memo[memo_id]}"

    def _handle_get(self, arg: Any) -> str:
        memo_id = self._memo_id(arg)
        self._push(self.memo.get(memo_id, _LiteralValue(f"memo[{memo_id}]")))
        return f"从 memo[{memo_id}] 取回对象"

    def _handle_memoize(self, _arg: Any) -> str:
        self.memo[self.memo_next_id] = self.stack[-1] if self.stack else "<empty>"
        meaning = f"写入 memo[{self.memo_next_id}] = {self.memo[self.memo_next_id]}"
        self.memo_next_id += 1
        return meaning

    def _handle_pop(self, _arg: Any) -> str:
        self._pop()
        return "弹出栈顶"

    def _handle_pop_mark(self, _arg: Any) -> str:
        self._pop_marked()
        return "弹出直到 MARK"

    def _handle_reduce(self, _arg: Any) -> str:
        args = self._pop()
        func = self._pop()
        rendered_call = self._render_reduce_call(func, args)
        self._push(_LiteralValue(rendered_call))
        return self._describe_reduce(func, args)

    def _handle_build(self, _arg: Any) -> str:
        state = self._pop()
        inst = self._pop()
        self._push(inst)
        return self._describe_build(inst, state)

    def _handle_newobj(self, _arg: Any) -> str:
        args = self._pop()
        cls = self._pop()
        rendered_call = self._render_call(cls, args)
        self._push(_LiteralValue(rendered_call))
        return f"调用 {rendered_call}"

    def _handle_newobj_ex(self, _arg: Any) -> str:
        kwargs = self._pop()
        args = self._pop()
        cls = self._pop()
        rendered_call = self._render_call(cls, args, kwargs)
        self._push(_LiteralValue(rendered_call))
        return f"调用 {rendered_call}"

    def _handle_obj(self, _arg: Any) -> str:
        items = self._pop_marked()
        if items:
            cls, args = items[0], items[1:]
        else:
            cls, args = _LiteralValue("<empty>"), []
        rendered_call = f"{cls}({self._join_items(args)})"
        self._push(_LiteralValue(rendered_call))
        return f"调用 {rendered_call}"

    def _handle_inst(self, arg: Any) -> str:
        args = self._pop_marked()
        rendered_args = self._join_items(args)
        if isinstance(arg, str) and " " in arg:
            module, name = arg.split(" ", 1)
            rendered_call = f"{module}.{name}({rendered_args})"
        else:
            rendered_call = f"{arg}({rendered_args})"
        self._push(_LiteralValue(rendered_call))
        return f"调用 {rendered_call}"


def explain(data: bytes) -> str:
    return _Explainer(data).render()
