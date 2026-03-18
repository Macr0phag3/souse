import ast
from typing import Any, Callable, Dict, List, Optional, Tuple

from .tools import put_color


class Opcodes:
    # Basic types
    INT = b'I'
    BININT = b'J'
    BININT1 = b'K'
    BININT2 = b'M'
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
    NEWOBJ_EX = b'\x92'


_GenerateSpec = Tuple[str, str]
_GenerateCache = Dict[_GenerateSpec, Callable[..., bytes]]
_GENERATE_CACHE: _GenerateCache = {}


def _load_generate(module_suffix: str, func_name: str = "generate") -> Callable[..., bytes]:
    key = (module_suffix, func_name)
    cached = _GENERATE_CACHE.get(key)
    if cached is not None:
        return cached

    module_name = f"{__package__}.{module_suffix}"
    module = __import__(module_name, fromlist=[func_name])
    func = getattr(module, func_name)
    _GENERATE_CACHE[key] = func
    return func


def generate_constant(gen, node: ast.Constant) -> bytes:
    value = node.value

    if value is True or value is False:
        return _load_generate("opcodegen.constant_bool")(gen, node)
    if value is None:
        return _load_generate("opcodegen.constant_none")(gen, node)

    if isinstance(value, str):
        return _load_generate("opcodegen.string")(gen, node)
    if isinstance(value, int):
        return _load_generate("opcodegen.constant_int")(gen, node)
    if isinstance(value, float):
        return _load_generate("opcodegen.constant_float")(gen, node)

    gen.ctx._error(node, f"this basic type is not supported yet: {value} ({type(value)})")


_HANDLER_SPECS: Dict[type, str] = {
    ast.Assign: "opcodegen.assign",
    ast.List: "opcodegen.list",
    ast.Set: "opcodegen.set",
    ast.Tuple: "opcodegen.tuple",
    ast.Dict: "opcodegen.dict",
    ast.ImportFrom: "opcodegen.import_from",
    ast.Name: "opcodegen.name",
    ast.Call: "opcodegen.call",
    ast.Attribute: "opcodegen.attribute",
    ast.Subscript: "opcodegen.subscript",
    ast.Slice: "opcodegen.slice",
    ast.UnaryOp: "opcodegen.unary",
}

HANDLERS: Dict[type, Callable[..., bytes]] = {
    ast.Constant: generate_constant,
}

for node_type, module_suffix in _HANDLER_SPECS.items():
    HANDLERS[node_type] = _load_generate(module_suffix)


def get_rule_key(gen, op: bytes) -> str:
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


def check_firewall(gen, opcodes: List[bytes], value: str = "*", node: Optional[ast.AST] = None) -> bytes:
    ctx = gen.ctx
    # filter disabled opcodes
    related_rules = {}
    for op in opcodes:
        key = get_rule_key(gen, op)
        if key in ctx.firewall_rules and ctx.firewall_rules[key] in [value, "*"]:
            related_rules[key] = ctx.firewall_rules[key]

    if not related_rules:
        return opcodes[0]

    # find bypass candidates
    bypass_opcodes = [op for op in opcodes if get_rule_key(gen, op) not in related_rules]

    if not bypass_opcodes:
        ctx._error(
            node,
            f"can NOT bypass: {put_color(related_rules, 'white')}, must use opcode in {put_color([get_rule_key(gen, op) for op in opcodes], 'white')}",
        )

    choice = bypass_opcodes[0]
    print(f"[*] choice {put_color(get_rule_key(gen, choice), 'blue')} to bypass rule: {put_color(related_rules, 'white')}")
    return choice


def to_converted_code(gen, node: ast.AST, is_assignment: bool = False) -> str:
    ctx = gen.ctx
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id in ctx.lazy_modules:
            return node.attr
        return f"getattr({to_converted_code(gen, node.value)}, \"{node.attr}\")"
    elif isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Tuple):
        return f"({', '.join([to_converted_code(gen, elt) for elt in node.elts])})"
    elif isinstance(node, ast.List):
        return f"[{', '.join([to_converted_code(gen, elt) for elt in node.elts])}]"
    elif isinstance(node, ast.Set):
        return f"{{{', '.join([to_converted_code(gen, elt) for elt in node.elts])}}}"
    elif isinstance(node, ast.Dict):
        items = []
        for k, v in zip(node.keys, node.values):
            if k is None:
                continue
            items.append(f"{to_converted_code(gen, k)}: {to_converted_code(gen, v)}")
        return f"{{{', '.join(items)}}}"
    elif isinstance(node, ast.Subscript):
        slice_node = node.slice
        if isinstance(slice_node, ast.Index):
            slice_node = getattr(slice_node, "value")

        if is_assignment:
            return f"{to_converted_code(gen, node.value)}[{to_converted_code(gen, slice_node)}]"
        return f"getattr({to_converted_code(gen, node.value)}, \"__getitem__\")({to_converted_code(gen, slice_node)})"
    elif isinstance(node, ast.Call):
        args = ", ".join([to_converted_code(gen, arg) for arg in node.args])
        return f"{to_converted_code(gen, node.func)}({args})"
    elif isinstance(node, ast.Slice):
        lower = to_converted_code(gen, node.lower) if node.lower else "None"
        upper = to_converted_code(gen, node.upper) if node.upper else "None"
        step = to_converted_code(gen, node.step) if node.step else "None"
        return f"slice({lower}, {upper}, {step})"
    elif isinstance(node, ast.Constant):
        return repr(node.value)
    elif isinstance(node, ast.UnaryOp):
        operand = to_converted_code(gen, node.operand)
        if isinstance(node.op, ast.USub):
            return f"-{operand}"
        elif isinstance(node.op, ast.UAdd):
            return f"+{operand}"
        elif isinstance(node.op, ast.Not):
            return f"not {operand}"
        elif isinstance(node.op, ast.Invert):
            return f"~{operand}"
    return ast.unparse(node)


class OpcodeGenerator:
    def __init__(self, ctx: Any) -> None:
        self.ctx = ctx

    def emit(self, node: ast.AST) -> bytes:
        handler = HANDLERS.get(type(node))
        if handler is None:
            self.ctx._error(node, f"this struct is not supported yet: {node.__class__.__name__}")
        return handler(self, node)  # type: ignore[call-arg]

    def get_rule_key(self, op: bytes) -> str:
        return get_rule_key(self, op)

    def check_firewall(self, opcodes: List[bytes], value: str = "*", node: Optional[ast.AST] = None) -> bytes:
        return check_firewall(self, opcodes, value=value, node=node)

    def to_converted_code(self, node: ast.AST, is_assignment: bool = False) -> str:
        return to_converted_code(self, node, is_assignment=is_assignment)


__all__ = [
    "Opcodes",
    "OpcodeGenerator",
    "HANDLERS",
    "check_firewall",
    "get_rule_key",
    "to_converted_code",
    "generate_constant",
]
