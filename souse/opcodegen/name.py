import ast
import builtins

from ..opcodes import Opcodes


def generate(gen, node: ast.Name) -> bytes:
    """
    对于一个变量来说，如果没有被定义过，那么
    1. 它要么是一个内置函数，需要通过 `from builtins import {name}` 来加载
    2. 它要么是一个已导入的模块，之前应该已经 import 过了
    3. 如果都不满足，就是未定义的变量
    """
    def _by_get() -> bytes:
        ctx = gen.ctx
        memo_name = ctx.names.get(node.id, [None, None])[0]
        if memo_name is None:
            # 自动处理内置函数
            if hasattr(builtins, node.id):
                import_node = ast.ImportFrom(
                    module="builtins",
                    names=[ast.alias(name=node.id, asname=None)],
                    level=0,
                )
                gen.ctx.has_transformation = True
                gen.ctx.queue_prefix_opcode(gen.emit(import_node))
                return Opcodes.GET + f"{gen.ctx.names[node.id][0]}\n".encode("utf-8")

            elif node.id in ctx.lazy_modules:
                # 自动处理已导入的模块：__import__(module_name)
                module_name = ctx.lazy_modules[node.id]
                import_call = ast.Call(
                    func=ast.Name(id="__import__", ctx=ast.Load()),
                    args=[ast.Constant(value=module_name)],
                    keywords=[],
                )
                opcode = gen.emit(import_call)
                opcode += Opcodes.PUT + f'{ctx.memo_id}\n'.encode('utf-8')

                ctx.names[node.id] = [str(ctx.memo_id), None]
                ctx.memo_id += 1
                gen.ctx.has_transformation = True
                ctx.converted_code.append(f'{node.id} = __import__({module_name!r})')
                gen.ctx.queue_prefix_opcode(opcode)
                return Opcodes.GET + f"{ctx.names[node.id][0]}\n".encode("utf-8")
            else:
                # 说明之前没有定义这个变量
                ctx._error(node, f"this var is not defined: {node.id}")

        return Opcodes.GET + f'{memo_name}\n'.encode('utf-8')

    bypass_map = {
        Opcodes.GET: _by_get,
    }
    choice = gen.check_firewall(list(bypass_map.keys()))
    return bypass_map[choice]()
