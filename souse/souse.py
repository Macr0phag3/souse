import os
import sys
import ast
import json
import pickle
import struct
import builtins
import argparse
import functools
import pickletools
from collections import Counter
from typing import Any, Dict, List, Optional, Union, Callable, Tuple, cast

from colorama import Fore, Style, init as Init # type: ignore


def put_color(string: Any, color: str, bold: bool = True) -> str:
    if color == 'gray':
        COLOR = Fore.LIGHTBLACK_EX
    else:
        COLOR = getattr(Fore, color.upper(), "WHITE")

    style = Style.BRIGHT if bold and color != 'gray' else ""
    return f'{style}{COLOR}{str(string)}{Style.RESET_ALL}'


def transfer_funcs(func_name: Optional[str]) -> Callable:
    if not func_name:
        return lambda x: x
    
    import base64
    import codecs
    import urllib.parse

    func = {
        'base64_encode': base64.b64encode,
        'hex_encode': functools.partial(codecs.encode, encoding="hex"),
        'url_decode': urllib.parse.quote_plus,
    }.get(FUNC_NAME.get(func_name, func_name))
    
    if func is None:
        raise RuntimeError(put_color(
            f"no such transfer function: {put_color(func_name, 'blue')}",
            "yellow"
        ))

    return cast(Callable, func)


class Opcodes:
    # Basic types
    INT = b'I'
    BININT = b'J'
    FLOAT = b'F'
    STRING = b'V'
    BINSTRING = b'S'
    NONE = b'N'
    TRUE = b'I01\n'
    BINTRUE = b'\x88'
    FALSE = b'I00\n'
    BINFALSE = b'\x89'
    
    # Collections
    MARK = b'('
    LIST = b'l'
    TUPLE = b't'
    DICT = b'd'
    EMPTY_SET = b'\x8f'
    ADDITEMS = b'\x90'

    # Operations
    REDUCE = b'R'
    OBJ = b'o'
    INST = b'i'
    GLOBAL = b'c'
    PUT = b'p'
    GET = b'g'
    STOP = b'.'
    
    # Dictionary/Attribute operations
    SETITEM = b's'
    SETITEMS = b'u'
    BUILD = b'b'
    EMPTY_DICT = b'}'
    NEWOBJ = b'\x81'


class Visitor(ast.NodeVisitor):
    def __init__(self, source_code: str, firewall_rules: Dict[str, str]) -> None:
        self.names: Dict[str, List[Optional[str]]] = {}  # 变量记录
        self.memo_id: int = 0  # memo 的顶层 id
        self.firewall_rules: Dict[str, str] = firewall_rules
        self.source_code: str = source_code
        self.lazy_modules: Dict[str, str] = {}  # import requests -> {'requests': 'requests'}

        self.final_opcode: bytes = b''
        self.code: str = ""
        self.result: bytes = b""
        self.converted_code: List[str] = []
        self.has_transformation: bool = False

    def souse(self) -> None:
        self.result = self.final_opcode + Opcodes.STOP

    def _ensure_builtins(self, name: str) -> str:
        if name not in self.names:
            self.names[name] = [cast(Optional[str], str(self.memo_id)), "builtins"]
            self.final_opcode += Opcodes.GLOBAL + f'builtins\n{name}\n'.encode('utf-8') + Opcodes.PUT + f'{self.memo_id}\n'.encode('utf-8')
            self.converted_code.append(f"from builtins import {name}")
            self.memo_id += 1
        return cast(str, self.names[name][0])

    def _ensure_module(self, alias: str) -> str:
        # 使用 __import__(name)
        if alias not in self.names:
            module_name = self.lazy_modules[alias]
            import_id = self._ensure_builtins("__import__")
            self.names[alias] = [cast(Optional[str], str(self.memo_id)), None]

            self.final_opcode += Opcodes.GET + f'{import_id}\n'.encode() + \
                                 Opcodes.MARK + Opcodes.STRING + f'{module_name}\n'.encode() + \
                                 Opcodes.TUPLE + Opcodes.REDUCE + \
                                 Opcodes.PUT + f'{self.memo_id}\n'.encode()
            
            # 记录转换后的代码
            log = f"import {module_name}" + (f" as {alias}" if alias != module_name else "")
            self.converted_code.append(log)

            self.memo_id += 1
        return cast(str, self.names[alias][0])

    def _parse_unary_op(self, node: ast.UnaryOp) -> bytes:
        if isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, (int, float)):
            # 简单的负数转换
            value = -cast(ast.Constant, node.operand).value
            new_node = ast.Constant(value=value)
            return self._parse_constant(new_node)
        
        self._error(node, f"this unary op is not supported yet: {node.op.__class__.__name__}")
        return b""

    def _get_rule_key(self, op: bytes) -> str:
        mapping = {
            Opcodes.BINTRUE: "\\x88",
            Opcodes.BINFALSE: "\\x89",
        }
        if op in mapping:
            return mapping[op]
        try:
            return op.decode().strip()
        except UnicodeDecodeError:
            return f"\\x{op[0]:02x}"

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

    def _check_firewall(self, opcodes: List[bytes], value: str = "*", node: Optional[ast.AST] = None) -> bytes:
        # 过滤被禁用的指令
        related_rules = {}
        for op in opcodes:
            key = self._get_rule_key(op)
            if key in self.firewall_rules and self.firewall_rules[key] in [value, "*"]:
                related_rules[key] = self.firewall_rules[key]
        
        if not related_rules:
            return opcodes[0]

        # 找没被禁用的
        bypass_opcodes = [op for op in opcodes if self._get_rule_key(op) not in related_rules]
        
        if not bypass_opcodes:
            self._error(node, f"can NOT bypass: {put_color(related_rules, 'white')}, must use opcode in {put_color([self._get_rule_key(op) for op in opcodes], 'white')}")
        
        choice = bypass_opcodes[0]
        print(f"[*] choice {put_color(self._get_rule_key(choice), 'blue')} to bypass rule: {put_color(related_rules, 'white')}")
        return choice

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
        with open('.souse-result.tmp', 'w') as fw:
            fw.write(
                'import pickle\n'
                f'print(pickle.loads({repr(self.result)}), end="")\n'
            )

        return os.popen(
            f"{sys.executable} .souse-result.tmp"
        ).read()

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
        ops: List[Tuple[pickletools.OpcodeInfo, Any, int]] = list(pickletools.genops(data))
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
        drop_indices: set[int] = set()
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

    def _flat(self, node: ast.AST) -> Any:
        '''递归处理基础的语句
        '''
        _types: Dict[Any, Any] = {
            ast.Constant: self._parse_constant,
            ast.List: self._parse_list,
            ast.Set: self._parse_set,
            ast.Tuple: self._parse_tuple,
            ast.Dict: self._parse_dict,
            ast.Name: self._parse_name,
            ast.Call: self._parse_call,
            ast.Attribute: self._parse_attribute,
            ast.Subscript: self._parse_subscript,
            ast.Slice: self._parse_slice,
            ast.UnaryOp: self._parse_unary_op,
        }

        for _type in _types:
            if isinstance(node, _type):
                return _types[_type](node)

        self._error(node, f"this struct is not supported yet: {node.__class__.__name__}")
        return b""

    def _to_converted_code(self, node: ast.AST, is_assignment: bool = False) -> str:
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id in self.lazy_modules:
                return node.attr
            return f"getattr({self._to_converted_code(node.value)}, \"{node.attr}\")"
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Tuple):
            return f"({', '.join([self._to_converted_code(elt) for elt in node.elts])})"
        elif isinstance(node, ast.List):
            return f"[{', '.join([self._to_converted_code(elt) for elt in node.elts])}]"
        elif isinstance(node, ast.Set):
            return f"{{{', '.join([self._to_converted_code(elt) for elt in node.elts])}}}"
        elif isinstance(node, ast.Dict):
            items = []
            for k, v in zip(node.keys, node.values):
                if k is None: continue
                items.append(f"{self._to_converted_code(cast(ast.AST, k))}: {self._to_converted_code(v)}")
            return f"{{{', '.join(items)}}}"
        elif isinstance(node, ast.Subscript):
            slice_node = node.slice
            if isinstance(slice_node, ast.Index):
                slice_node = getattr(slice_node, 'value')
            
            if is_assignment:
                return f"{self._to_converted_code(node.value)}[{self._to_converted_code(slice_node)}]"
            return f"getattr({self._to_converted_code(node.value)}, \"__getitem__\")({self._to_converted_code(slice_node)})"
        elif isinstance(node, ast.Call):
            args = ", ".join([self._to_converted_code(arg) for arg in node.args])
            return f"{self._to_converted_code(node.func)}({args})"
        elif isinstance(node, ast.Slice):
            lower = self._to_converted_code(cast(ast.AST, node.lower)) if node.lower else "None"
            upper = self._to_converted_code(cast(ast.AST, node.upper)) if node.upper else "None"
            step = self._to_converted_code(cast(ast.AST, node.step)) if node.step else "None"
            return f"slice({lower}, {upper}, {step})"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.UnaryOp):
            operand = self._to_converted_code(node.operand)
            if isinstance(node.op, ast.USub):
                return f"-{operand}"
            elif isinstance(node.op, ast.UAdd):
                return f"+{operand}"
            elif isinstance(node.op, ast.Not):
                return f"not {operand}"
            elif isinstance(node.op, ast.Invert):
                return f"~{operand}"
        return ast.unparse(node)

    def _parse_constant(self, node: ast.Constant) -> bytes:
        def __generate_int():
            opcodes = [Opcodes.INT, Opcodes.BININT]
            choice = self._check_firewall(opcodes, value=str(node.value), node=node)
            
            if choice == Opcodes.BININT:
                return Opcodes.BININT + struct.pack('<i', node.value)
            return Opcodes.INT + f'{node.value}\n'.encode()

        def __generate_float():
            return Opcodes.FLOAT + f'{node.value}\n'.encode()

        def __generate_str():
            # 仅当内容是 ASCII 时，BINSTRING 才能安全表示。
            literal_bytes = None
            if all(ord(ch) < 128 for ch in node.value):
                # STRING 指令要求 ASCII 的 Python 字面量；repr() 会做正确转义。
                literal_bytes = repr(node.value).encode("ascii")

            opcodes = [Opcodes.STRING, Opcodes.BINSTRING] if literal_bytes is not None else [Opcodes.STRING]
            choice = self._check_firewall(opcodes, value=str(node.value), node=node)
            
            if choice == Opcodes.BINSTRING:
                return Opcodes.BINSTRING + literal_bytes + b"\n"

            # UNICODE (V) 需要 protocol 0 的转义格式；交给 pickle 生成最规范的 payload。
            payload = pickle.dumps(node.value, protocol=0)
            if not payload.startswith(Opcodes.STRING):
                # 理论上不会触发
                self._error(node, "unexpected pickle encoding for unicode string")

            end = payload.index(b"\n", 1)
            return Opcodes.STRING + payload[1:end] + b"\n"

        def __generate_none():
            return Opcodes.NONE

        def __generate_true():
            opcodes = [Opcodes.TRUE, Opcodes.BINTRUE]
            return self._check_firewall(opcodes, node=node)

        def __generate_false():
            opcodes = [Opcodes.FALSE, Opcodes.BINFALSE]
            return self._check_firewall(opcodes, node=node)

        value_map: Dict[Any, Any] = {
            int: __generate_int,
            float: __generate_float,
            str: __generate_str,

            None: __generate_none,
            True: __generate_true,
            False: __generate_false,
        }
        generate_func = (
            value_map.get(type(node.value), None)
            or
            value_map.get(node.value, None)
        )
        if generate_func is None:
            self._error(node, f"this basic type is not supported yet: {node.value} ({type(node.value)})")
            return b""

        result = generate_func()
        if isinstance(result, str):
            result = result.encode()

        return result

    def _parse_set(self, node: ast.Set) -> Any:
        # PVM Protocol 4
        return (
            Opcodes.EMPTY_SET +
            b"".join([self._flat(elt) for elt in node.elts]) +
            Opcodes.ADDITEMS
        )

    def _parse_list(self, node: ast.List) -> bytes:
        return (
            Opcodes.MARK +
            b"".join([self._flat(elt) for elt in node.elts]) +
            Opcodes.LIST
        )

    def _parse_tuple(self, node: ast.Tuple) -> bytes:
        return (
            Opcodes.MARK +
            b"".join([self._flat(elt) for elt in node.elts]) +
            Opcodes.TUPLE
        )

    def _parse_dict(self, node: ast.Dict) -> bytes:
        return (
            Opcodes.MARK +
            b"".join([self._flat(k) + self._flat(v) for k, v in zip(node.keys, node.values) if k is not None]) +
            Opcodes.DICT
        )

    def _parse_name(self, node: ast.Name) -> Any:
        memo_name = self.names.get(node.id, [None, None])[0]
        if memo_name is None:
            # 自动处理内置函数
            if hasattr(builtins, node.id):
                memo_name = self._ensure_builtins(node.id)
            elif node.id in self.lazy_modules:
                # 自动处理已导入的模块
                memo_name = self._ensure_module(node.id)
            else:
                # 说明之前没有定义这个变量
                self._error(node, f"this var is not defined: {node.id}")
                return b""

        return Opcodes.GET + f'{memo_name}\n'.encode('utf-8')

    def _parse_attribute(self, node: ast.Attribute) -> bytes:
        targets = node.value
        attr = node.attr

        if isinstance(targets, ast.Name):
            if targets.id in self.lazy_modules:
                # 如果已经 import 了，直接获取
                module_name = self.lazy_modules[targets.id]
                full_name = f"{module_name}.{attr}"
                if full_name not in self.names:
                    self.names[full_name] = [cast(Optional[str], str(self.memo_id)), module_name]
                    self.final_opcode += Opcodes.GLOBAL + f'{module_name}\n{attr}\n'.encode('utf-8') + Opcodes.PUT + f'{self.memo_id}\n'.encode('utf-8')
                    self.converted_code.append(f"from {module_name} import {attr}")
                    self.memo_id += 1
                    self.has_transformation = True
                return Opcodes.GET + f'{cast(str, self.names[full_name][0])}\n'.encode('utf-8')

        # 否则就用 getattr(obj, attr)
        getattr_id = self._ensure_builtins("getattr")
        self.has_transformation = True
        obj_opcode = self._flat(targets)
        return Opcodes.GET + f'{getattr_id}\n'.encode() + Opcodes.MARK + obj_opcode + Opcodes.STRING + f'{attr}\n'.encode() + Opcodes.TUPLE + Opcodes.REDUCE

    def _parse_slice(self, node: ast.Slice) -> bytes:
        slice_id = self._ensure_builtins("slice")
        self.has_transformation = True
        
        lower = self._flat(cast(ast.AST, node.lower)) if node.lower else Opcodes.NONE
        upper = self._flat(cast(ast.AST, node.upper)) if node.upper else Opcodes.NONE
        step = self._flat(cast(ast.AST, node.step)) if node.step else Opcodes.NONE

        return Opcodes.GET + f'{slice_id}\n'.encode() + \
               Opcodes.MARK + lower + upper + step + \
               Opcodes.TUPLE + Opcodes.REDUCE

    def _parse_subscript(self, node: ast.Subscript) -> bytes:
        # 加载模式: obj[key] -> getattr(obj, "__getitem__")(key)
        getattr_id = self._ensure_builtins("getattr")
        self.has_transformation = True
        getattr_id_bytes = f'{getattr_id}\n'.encode()

        slice_node = node.slice
        if isinstance(slice_node, ast.Index):
            # 兼容 py < 3.9
            slice_node = getattr(slice_node, 'value')

        obj_opcode = self._flat(node.value)
        key_opcode = self._flat(slice_node)

        # getattr(obj, "__getitem__")
        m1 = Opcodes.GET + getattr_id_bytes + Opcodes.MARK + obj_opcode + Opcodes.STRING + b"__getitem__\n" + Opcodes.TUPLE + Opcodes.REDUCE
        # (key)
        return m1 + Opcodes.MARK + key_opcode + Opcodes.TUPLE + Opcodes.REDUCE

    def _parse_call(self, node: ast.Call) -> bytes:
        def _normal_generate(node) -> bytes:
            if isinstance(node.func, (ast.Name, ast.Call, ast.Attribute)):
                opcode = Opcodes.MARK + b"".join([self._flat(arg) for arg in node.args]) + Opcodes.TUPLE + Opcodes.REDUCE
            else:
                self._error(node.func, f"this function call is not supported yet: {node.func.__class__}")
                return b"" # Should not reach here due to _error raising

            func_opcode = self._flat(node.func)
            return func_opcode + opcode

        def _obj_generate(node) -> bytes:
            func_opcode = self._flat(node.func)
            if isinstance(node.func, (ast.Call, ast.Name, ast.Attribute)):
                return Opcodes.MARK + func_opcode + b"".join([self._flat(arg) for arg in node.args]) + Opcodes.OBJ
            
            self._error(node.func, f"this object call is not supported yet: {node.func.__class__.__name__}")
            return b""

        def _instance_generate(node) -> bytes:
            func_opcode = self._flat(node.func)
            # func_opcode should be like b'g1\n' or b'cmodule\nname\n'
            opcode_str = func_opcode.decode().strip()
            code = opcode_str[0]
            num = opcode_str[1:]

            imported_func = [
                (cast(str, j[1]), i)
                for i, j in self.names.items()
                if j[0] == num and j[1]
            ]
            if code != 'g' or not imported_func:
                self._error(node, f"can NOT bypass with 'i': function must be imported first")
                return b""

            module_name, func_name = imported_func[0]
            if isinstance(node.func, (ast.Name, ast.Attribute)):
                return Opcodes.MARK + b"".join([self._flat(arg) for arg in node.args]) + Opcodes.INST + f"{module_name}\n{func_name}\n".encode()
            
            self._error(node.func, f"this instance call is not supported yet: {node.func.__class__.__name__}")
            return b""

        def _can_newobj(node: ast.Call) -> bool:
            if node.keywords:
                # NEWOBJ does not support keyword args
                return False

            func = node.func

            def _is_builtin_type(name: str) -> bool:
                obj = getattr(builtins, name, None)
                if not isinstance(obj, type):
                    print(put_color("[!] NEWOBJ (\\x81) only supports type (class), so bypass may be failed\n", "yellow"))
                return True

            if isinstance(func, ast.Name):
                return _is_builtin_type(func.id)

            if isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name) and func.value.id == "builtins":
                    return _is_builtin_type(func.attr)

            return False

        def _newobj_generate(node) -> bytes:
            # NEWOBJ: cls args_tuple \x81
            func_opcode = self._flat(node.func)
            args_opcode = Opcodes.MARK + b"".join([self._flat(arg) for arg in node.args]) + Opcodes.TUPLE
            return func_opcode + args_opcode + Opcodes.NEWOBJ

        opcodes = [Opcodes.REDUCE, Opcodes.OBJ, Opcodes.INST]
        if _can_newobj(node):
            opcodes.append(Opcodes.NEWOBJ)

        choice = self._check_firewall(opcodes, node=node)

        if choice == Opcodes.REDUCE:
            return _normal_generate(node)
        elif choice == Opcodes.OBJ:
            return _obj_generate(node)
        elif choice == Opcodes.INST:
            return _instance_generate(node)
        elif choice == Opcodes.NEWOBJ:
            return _newobj_generate(node)
        
        self._error(node, "unsupported call bypass choice")
        return b""

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
        def _generate_opcode():
            for _name in node.names:
                name = _name.asname or _name.name
                self.names[name] = [cast(Optional[str], str(self.memo_id)), node.module]
                self.final_opcode += Opcodes.GLOBAL + f'{node.module}\n{name}\n'.encode('utf-8') + Opcodes.PUT + f'{self.memo_id}\n'.encode('utf-8')
                as_suffix = f" as {_name.asname}" if _name.asname else ""
                self.converted_code.append(f"from {node.module} import {_name.name}{as_suffix}")
                self.memo_id += 1

        _generate_opcode()

    def visit_Assign(self, node: ast.Assign) -> None:
        # 赋值
        # a = "whoami"
        def _generate_opcode():
            if isinstance(node.targets[0], ast.Tuple):
                self._error(node.targets[0], f"mass assignment is not supported yet, unpack it!")

            # 1. 分析等号右边 (可能触发导入，先处理以保证顺序)
            right_opcode = self._flat(node.value)
            right_str = self._to_converted_code(node.value)

            # 2. 分析等号左边并生成指令
            if isinstance(node.targets[0], ast.Name):
                # eg: a = ...
                target_name = cast(ast.Name, node.targets[0])
                name = target_name.id
                assign_opcode = b'{right_opcode}' + Opcodes.PUT + f'{self.memo_id}\n'.encode("utf-8")

                self.names[name] = [cast(Optional[str], str(self.memo_id)), None]
                self.converted_code.append(f"{name} = {right_str}")
                self.memo_id += 1

            elif isinstance(node.targets[0], ast.Attribute):
                # eg: os.system = "whoami"
                target_attr = cast(ast.Attribute, node.targets[0])
                if isinstance(target_attr.value, ast.Name) and target_attr.value.id in self.lazy_modules:
                    module_name = self.lazy_modules[target_attr.value.id]
                    attr_name = target_attr.attr
                    full_name = f"{module_name}.{attr_name}"

                    if full_name not in self.names:
                        self.names[full_name] = [cast(Optional[str], str(self.memo_id)), module_name]
                        self.final_opcode += Opcodes.GLOBAL + f'{module_name}\n{attr_name}\n'.encode('utf-8') + Opcodes.PUT + f'{self.memo_id}\n'.encode('utf-8')
                        self.converted_code.append(f"from {module_name} import {attr_name}")
                        self.memo_id += 1
                        self.has_transformation = True

                    assign_opcode = b'{right_opcode}' + Opcodes.PUT + f'{self.memo_id}\n'.encode("utf-8")

                    self.names[full_name] = [cast(Optional[str], str(self.memo_id)), None]
                    self.converted_code.append(f"{attr_name} = {right_str}")
                    self.memo_id += 1
                else:
                    # 否则就用 getattr(obj, attr)
                    left_opcode = self._flat(target_attr.value)
                    left_str = self._to_converted_code(target_attr.value)
                    attr_name = target_attr.attr

                    # 检查 'b' (BUILD) 是否被禁用
                    choice = self._check_firewall([Opcodes.BUILD], node=node)

                    if choice == Opcodes.BUILD:
                        assign_opcode = b'{left_opcode}' + Opcodes.MARK + Opcodes.NONE + Opcodes.EMPTY_DICT + b'V{attr}\n{right_opcode}' + Opcodes.SETITEM + Opcodes.TUPLE + Opcodes.BUILD
                        assign_opcode = assign_opcode \
                                        .replace(b'{left_opcode}', left_opcode) \
                                        .replace(b'{attr}', attr_name.encode())
                        self.converted_code.append(f"{left_str}.{attr_name} = {right_str}")
                    else:
                        # 使用 setattr(obj, attr, val)
                        print(f"[*] choice {put_color('setattr', 'blue')} to bypass rule: {put_color({'b': '*'}, 'white')}")
                        setattr_id = self._ensure_builtins("setattr")
                        self.has_transformation = True
                        assign_opcode = Opcodes.GET + f'{setattr_id}\n'.encode() + Opcodes.MARK + left_opcode + Opcodes.STRING + f'{attr_name}\n'.encode() + b'{right_opcode}' + Opcodes.TUPLE + Opcodes.REDUCE
                        
                        self.converted_code.append(f"setattr({left_str}, \"{attr_name}\", {right_str})")

            elif isinstance(node.targets[0], ast.Subscript):
                # eg: a["test"] = ...
                target_sub = cast(ast.Subscript, node.targets[0])
                slice_node = target_sub.slice
                if isinstance(slice_node, ast.Index):
                    slice_node = getattr(slice_node, 'value')

                # 检查 'u' (SETITEMS) 是否被禁用
                u_disabled = "u" in self.firewall_rules and self.firewall_rules["u"] == "*"

                inside_opcode = self._flat(slice_node)
                outside_opcode = self._flat(target_sub.value)
                inside_str = self._to_converted_code(slice_node)
                outside_str = self._to_converted_code(target_sub.value)

                if not u_disabled:
                    assign_opcode = b'{outside_opcode}' + Opcodes.MARK + b'{inside_opcode}{right_opcode}' + Opcodes.SETITEMS
                    assign_opcode = assign_opcode \
                                    .replace(b'{outside_opcode}', outside_opcode) \
                                    .replace(b'{inside_opcode}', inside_opcode)
                    self.converted_code.append(f"{outside_str}[{inside_str}] = {right_str}")
                else:
                    # 使用 getattr(obj, "__setitem__")(key, val)
                    print(f"[*] choice {put_color('__setitem__', 'blue')} to bypass rule: {put_color({'u': '*'}, 'white')}")
                    getattr_id = self._ensure_builtins("getattr")
                    self.has_transformation = True
                    assign_opcode = Opcodes.GET + f'{getattr_id}\n'.encode() + Opcodes.MARK + outside_opcode + Opcodes.STRING + b"__setitem__\n" + Opcodes.TUPLE + Opcodes.REDUCE + Opcodes.MARK + inside_opcode + b"{right_opcode}" + Opcodes.TUPLE + Opcodes.REDUCE
                    
                    self.converted_code.append(f"getattr({outside_str}, \"__setitem__\")({inside_str}, {right_str})")

            else:
                raise RuntimeError(
                    put_color("this complex assignment is not supported yet: ", "red") +
                    f"{put_color(node.targets[0].__class__, 'cyan')} in the left part of {self.code}"
                )

            self.final_opcode += assign_opcode.replace(b"{right_opcode}", right_opcode)

        start = node.lineno - 1
        end = getattr(node, 'end_lineno', None)
        end = end if end is not None else node.lineno
        self.code = put_color("\n".join(
            self.source_code.split('\n')[start:end]  # type: ignore
        ), "white")
        _generate_opcode()

    def _visit_expr_stmt(self, node: ast.AST) -> None:
        # 统一处理“表达式语句”
        def _generate_opcode():
            opcode = self._flat(node)
            self.converted_code.append(self._to_converted_code(node))
            self.final_opcode += opcode

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


class API:
    def __init__(self, source_code: str, firewall_rules: Optional[Dict[str, str]] = None, optimized: bool = True, transfer: Union[str, Callable[..., Any], List[Callable[..., Any]], None] = '') -> None:
        self.source_code = source_code
        self.root = ast.parse(self.source_code)
        self.firewall_rules = firewall_rules or {}
        self.optimized = optimized
        self.transfer = transfer

    def _generate(self) -> Visitor:
        visitor = Visitor(
            self.source_code, self.firewall_rules
        )
        visitor.visit(self.root)
        visitor.souse()
        return visitor

    def generate(self) -> Any:
        visitor = Visitor(
            self.source_code,
            self.firewall_rules,
        )
        visitor.visit(self.root)
        visitor.souse()

        result = visitor.result

        if self.optimized:
            result = visitor.optimize()

        transfer = self.transfer

        if isinstance(transfer, list):
            for func in transfer:
                result = func(result)

            return result

        if transfer is None or isinstance(transfer, str):
            transfer = transfer_funcs(transfer)
            self.transfer = transfer

        if callable(transfer):
            return transfer(result)
        return result


def cli() -> None:
    Init()
    print(LOGO)

    parser = argparse.ArgumentParser(description=f'Version: {VERSION}; Running in Py3.x')
    parser.add_argument(
        "--check", action="store_true",
        help="run pickle.loads() to test opcode"
    )
    parser.add_argument(
        "--no-optimize", action="store_false",
        help="do NOT optimize opcode"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--filename", help=".py source code filename")
    group.add_argument(
        "--run-test", action="store_true",
        help="run test with test/*.py (not startswith `N-`)"
    )
    parser.add_argument(
        "-p", "--bypass", default=False,
        help="try bypass limitation"
    )
    parser.add_argument(
        "-t", "--transfer", default=None,
        help=f"transfer result with: { {i for i in FUNC_NAME.values()} }"
    )

    args = parser.parse_args()

    need_check = args.check
    need_optimize = args.no_optimize
    run_test = args.run_test
    transfer = args.transfer
    transfer_func = transfer_funcs(transfer)

    if run_test:
        # 代码质量测试模式下
        # 不优化 opcode、不执行 opcode、不 bypass
        need_optimize = False
        need_check = False
        bypass = False
        directory = os.path.join(
            os.path.dirname(__file__), "test"
        )
        filenames = sorted([
            os.path.join(directory, i) for i in list(os.walk(directory))[0][2]
            if not i.startswith("N-")
        ])
    else:
        filenames = [args.filename]

    print(f'[*] need check:        {put_color(need_check, ["gray", "green"][int(need_check)])}')
    print(f'[*] need optimize:     {put_color(need_optimize, ["gray", "green"][int(need_optimize)])}')

    firewall_rules = {}
    bypass = False
    if args.bypass:
        try:
            firewall_rules = json.loads(args.bypass)
        except Exception as e:
            try:
                firewall_rules = json.load(open(args.bypass, encoding='utf-8'))
            except Exception as e:
                print("\n[!]", put_color(f"{args.bypass} has invalid bypass rules: {e}\n", 'yellow'))
            else:
                if not firewall_rules:
                    print("\n[!]", put_color(f"{args.bypass} has no rules\n", 'yellow'))
                else:
                    bypass = True

    print(f'[*] try bypass:        {put_color(args.bypass, ["gray", "cyan"][int(bypass)])}')
    print(f'[*] transfer function: {put_color(transfer, ["blue", "gray"][bool(bypass)])}\n')
    for filename in filenames:
        def tip(c): return f'[+] input: {put_color(filename, c)}'

        source_code = open(filename, encoding='utf-8').read()
        try:
            visitor = API(
                source_code, firewall_rules, need_optimize,
            )._generate()
        except Exception:
            print(tip("red"), end="\n\n")
            raise
        else:
            if run_test:
                answer = [
                    i.replace("# ", "").strip()
                    for i in source_code.split('\n') if i.strip()
                ][-1]
                correct = answer == str(visitor.result)
                if correct:
                    print(tip("green"))
                    continue
                else:
                    print(tip("yellow"))
            else:
                print(tip("cyan"))

        print(f'  [-] raw opcode:         {put_color(visitor.result, "green")}')

        if need_optimize:
            print(f'  [-] optimized opcode:   {put_color(visitor.optimize(), "green")}')

            if transfer:
                print(f'  [-] transfered opcode:  {put_color(transfer_func(visitor.optimize()), "green")}')

        elif transfer:
            print(f'  [-] transfered opcode:  {put_color(transfer_func(visitor.result), "green")}')

        if need_check:
            print(f'  [-] opcode test result: {put_color(visitor.check(), "white")}')

        if visitor.has_transformation and visitor.converted_code:
            print(f'  [-] converted code: ')
            for line in visitor.converted_code:
                print(f'      {put_color(line, "gray")}')

        if run_test:
            loc = [
                (i, j)
                for i, j in zip(enumerate(str(visitor.result)), enumerate(answer))
                if i[1] != j[1]
            ][0][0][0]
            answer = (
                put_color(answer[:loc], "green") + put_color(answer[loc:-1], "yellow") + put_color(answer[-1], "green") # type: ignore
            )
            print(f'  [-] answer for test:    {answer}')

    print("\n[*] done")


VERSION = '4.1'
LOGO = (
    f'''
  ██████  ▒█████   █    ██   ██████ ▓█████ 
▒██    ▒ ▒██▒  ██▒ ██  ▓██▒▒██    ▒ ▓█   ▀ 
░ ▓██▄   ▒██░  ██▒▓██  ▒██░░ ▓██▄   ▒███   
  ▒   ██▒▒██   ██░▓▓█  ░██░  ▒   ██▒▒▓█  ▄ 
▒██████▒▒░ ████▓▒░▒▒█████▓ ▒██████▒▒░▒████▒
▒ ▒▓▒ ▒ ░░ ▒░▒░▒░ ░▒▓▒ ▒ ▒ ▒ ▒▓▒ ▒ ░░░ ▒░ ░
░ ░▒  ░ ░  ░ ▒ ▒░ ░░▒░ ░ ░ ░ ░▒  ░ ░ ░ ░  ░
░  ░  ░  ░ ░ ░ ▒   ░░░ ░ ░ ░  ░  ░     ░   
      ░      ░ ░     ░           ░     ░  ░ v{Fore.GREEN}{VERSION}{Style.RESET_ALL}
'''
    .replace('█', put_color('█', "yellow"))
    .replace('▒', put_color('▒', "yellow", bold=False))
    .replace('▓', put_color('▓', "yellow"))
    .replace('░', put_color('░', "white", bold=False))
    .replace('▀', put_color('▀', "yellow"))
    .replace('▄', put_color('▄', "yellow"))
)

FUNC_NAME = {
    "b64": "base64_encode",
    "base64": "base64_encode",
    "base64encode": "base64_encode",

    "hex": "hex_encode",
    "hexencode": "hex_encode",

    "url": "url_decode",
    "urldecode": "url_decode",
}

if __name__ == '__main__':
    cli()
