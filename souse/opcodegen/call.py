import ast
import builtins

from ..opcodes import Opcodes
from ..tools import put_color


def generate(gen, node: ast.Call) -> bytes:
    def _by_reduce() -> bytes:
        if isinstance(node.func, (ast.Name, ast.Call, ast.Attribute)):
            func_opcode = gen.emit(node.func)
            args_tuple = ast.Tuple(elts=list(node.args), ctx=ast.Load())
            args_opcode = gen.emit(args_tuple)
        else:
            gen.ctx._error(node.func, f"this function call is not supported yet: {node.func.__class__}")

        return func_opcode + args_opcode + Opcodes.REDUCE

    def _by_obj() -> bytes:
        func_opcode = gen.emit(node.func)
        if isinstance(node.func, (ast.Call, ast.Name, ast.Attribute)):
            return Opcodes.MARK + func_opcode + b"".join([gen.emit(arg) for arg in node.args]) + Opcodes.OBJ

        gen.ctx._error(node.func, f"this object call is not supported yet: {node.func.__class__.__name__}")

    def _by_inst() -> bytes:
        ctx = gen.ctx
        func_opcode = gen.emit(node.func)
        # func_opcode should be like b'g1\n' or b'cmodule\nname\n'
        opcode_str = func_opcode.decode().strip()
        code = opcode_str[0]
        num = opcode_str[1:]

        imported_func = [
            (j[1], i)
            for i, j in ctx.names.items()
            if j[0] == num and j[1]
        ]
        if code != 'g' or not imported_func:
            ctx._error(node, f"can NOT bypass with 'i': function must be imported first")

        module_name, func_name = imported_func[0]
        if isinstance(node.func, (ast.Name, ast.Attribute)):
            return Opcodes.MARK + b"".join([gen.emit(arg) for arg in node.args]) + Opcodes.INST + f"{module_name}\n{func_name}\n".encode()

        ctx._error(node.func, f"this instance call is not supported yet: {node.func.__class__.__name__}")

    def _is_builtin_type(name: str, opcode_label: str) -> bool:
        obj = getattr(builtins, name, None)
        if not isinstance(obj, type):
            print(put_color(f"[!] {opcode_label} requires a type (class); this bypass may fail at runtime.\n", "yellow"))
        return True

    def _can_newobj_like(opcode_label: str, require_keywords: bool) -> bool:
        if require_keywords:
            if not node.keywords:
                # NEWOBJ_EX requires keyword args
                return False
        else:
            if node.keywords:
                # NEWOBJ does not support keyword args
                return False

        func = node.func
        if isinstance(func, ast.Name):
            return _is_builtin_type(func.id, opcode_label)

        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name) and func.value.id == "builtins":
                return _is_builtin_type(func.attr, opcode_label)

        return False

    def _can_newobj() -> bool:
        return _can_newobj_like("NEWOBJ (\\x81)", require_keywords=False)

    def _can_newobj_ex() -> bool:
        return _can_newobj_like("NEWOBJ_EX (\\x92)", require_keywords=True)

    def _by_newobj() -> bytes:
        if not _can_newobj():
            gen.ctx._error(node, "unsupported call bypass choice")

        # NEWOBJ: cls args_tuple \x81
        func_opcode = gen.emit(node.func)
        args_tuple = ast.Tuple(elts=list(node.args), ctx=ast.Load())
        args_opcode = gen.emit(args_tuple)
        return func_opcode + args_opcode + Opcodes.NEWOBJ

    def _by_newobj_ex() -> bytes:
        if not _can_newobj_ex():
            gen.ctx._error(node, "unsupported call bypass choice")

        # NEWOBJ_EX: cls args_tuple kwargs_dict \x92
        func_opcode = gen.emit(node.func)
        args_tuple = ast.Tuple(elts=list(node.args), ctx=ast.Load())
        args_opcode = gen.emit(args_tuple)

        kv_opcodes = []
        for kw in node.keywords:
            key_node = ast.Constant(value=kw.arg)
            kv_opcodes.append(gen.emit(key_node))
            kv_opcodes.append(gen.emit(kw.value))

        kwargs_opcode = Opcodes.MARK + b"".join(kv_opcodes) + Opcodes.DICT
        return func_opcode + args_opcode + kwargs_opcode + Opcodes.NEWOBJ_EX

    bypass_map = {
        Opcodes.REDUCE: _by_reduce,
        Opcodes.OBJ: _by_obj,
        Opcodes.INST: _by_inst,
        Opcodes.NEWOBJ: _by_newobj,
    }

    if _can_newobj_ex():
        bypass_map[Opcodes.NEWOBJ_EX] = _by_newobj_ex

    choice = gen.check_firewall(list(bypass_map.keys()))
    return bypass_map[choice]()
