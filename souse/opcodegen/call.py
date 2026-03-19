import ast
import builtins

from ..opcodes import Opcodes
from ..tools import put_color


def generate(gen, node: ast.Call) -> bytes:
    def _by_reduce() -> bytes:
        func_opcode = gen.emit(node.func)
        args_tuple = ast.Tuple(elts=list(node.args), ctx=ast.Load())
        args_opcode = gen.emit(args_tuple)
        return func_opcode + args_opcode + Opcodes.REDUCE

    def _by_obj() -> bytes:
        func_opcode = gen.emit(node.func)
        return Opcodes.MARK + func_opcode + b"".join([gen.emit(arg) for arg in node.args]) + Opcodes.OBJ

    def _by_inst() -> bytes | None:
        """
        INST 需要把调用目标还原成 module_name + func_name
        因此这里只支持能反查到导入来源的调用
        像 len("1") 这种经过前置转换 from builtins import len 后也可以支持
        但复杂语句无法支持，如：getattr(os, "system")("whoami")
        """

        ctx = gen.ctx
        func_opcode = gen.emit(node.func)
        opcode_str = func_opcode.decode().strip()
        code = opcode_str[0]
        num = opcode_str[1:]

        imported_func = [
            (j[1], i)
            for i, j in ctx.names.items()
            if j[0] == num and j[1]
        ]
        if code != 'g' or not imported_func:
            return None

        module_name, func_name = imported_func[0]
        return Opcodes.MARK + b"".join([gen.emit(arg) for arg in node.args]) + Opcodes.INST + f"{module_name}\n{func_name}\n".encode()

    def _by_newobj_like(need_keywords: bool = False) -> bytes:
        type_name = "NEWOBJ (\\x81)" if not need_keywords else "NEWOBJ_EX (\\x92)"
        warn = put_color(f"[!] {type_name} requires a type (class), this bypass may fail at runtime. But we have no choice :)\n", "yellow")
        if isinstance(node.func, ast.Name):
            obj = getattr(builtins, node.func.id, None)
            if not isinstance(obj, type):
                print(warn)
        elif isinstance(node.func, ast.Attribute):
            obj = getattr(builtins, node.func.attr, None)
            if not isinstance(obj, type):
                print(warn)

        func_opcode = gen.emit(node.func)
        args_tuple = ast.Tuple(elts=list(node.args), ctx=ast.Load())
        args_opcode = gen.emit(args_tuple)
        if not need_keywords:
            return func_opcode + args_opcode + Opcodes.NEWOBJ

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
    }

    if not node.keywords:
        bypass_map[Opcodes.NEWOBJ] = lambda: _by_newobj_like(False)

    if node.keywords:
        bypass_map[Opcodes.NEWOBJ_EX] = lambda: _by_newobj_like(True)

    return gen.generate_with_firewall(bypass_map, node=node)
