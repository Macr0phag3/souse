import ast

from ..opcodes import Opcodes


def generate(gen, node: ast.Attribute) -> bytes:
    def _by_imported(module_name: str, attr: str, full_name: str) -> bytes:
        """
        用 from module import attr 来获取
        """
        ctx = gen.ctx
        if full_name not in ctx.names:
            ctx.names[full_name] = [str(ctx.memo_id), module_name]
            opcode = (
                Opcodes.GLOBAL
                + f'{module_name}\n{attr}\n'.encode('utf-8')
                + Opcodes.PUT
                + f'{ctx.memo_id}\n'.encode('utf-8')
            )
            ctx.converted_code.append(f"from {module_name} import {attr}")
            ctx.memo_id += 1
            ctx.has_transformation = True
            ctx.queue_prefix_opcode(opcode)
        return Opcodes.GET + f'{ctx.names[full_name][0]}\n'.encode('utf-8')

    def _by_getattr() -> bytes:
        """
        用 getattr(obj, attr) 来获取
        """
        ctx = gen.ctx
        targets = node.value
        attr = node.attr

        ctx.has_transformation = True
        call_node = ast.Call(
            func=ast.Name(id="getattr", ctx=ast.Load()),
            args=[
                targets,
                ast.Constant(value=attr),
            ],
            keywords=[],
        )
        return gen.emit(call_node)

    ctx = gen.ctx
    targets = node.value
    attr = node.attr

    bypass_map = {
        "R": _by_getattr,
    }

    if isinstance(targets, ast.Name) and targets.id in ctx.lazy_modules:
        # 如果已经 import 了，可以直接获取
        module_name = ctx.lazy_modules[targets.id]
        full_name = f"{module_name}.{attr}"
        bypass_map = {
            "c": lambda: _by_imported(module_name, attr, full_name),
            "R": _by_getattr,
        }
    else:
        bypass_map = {
            "R": _by_getattr,
        }

    return gen.generate_with_firewall(bypass_map, node=node)
