import ast

from ..opcodes import Opcodes
from ..tools import put_color


def generate(gen, node: ast.Assign) -> bytes:
    """
    处理赋值操作

    这里会出现很多需要获取 attr 的操作
    但是比较可惜没法通过递归复用 attribute.py
    因为它有一个 from module import attr 这里几乎无法使用
    """

    ctx = gen.ctx

    if isinstance(node.targets[0], ast.Tuple):
        ctx._error(node.targets[0], "mass assignment is not supported yet, unpack it!")

    if isinstance(node.targets[0], ast.Name):
        # 等号左侧是非常直接的变量名
        # eg: a = ...
        name = node.targets[0].id
        right_opcode = gen.emit(node.value)
        right_str = gen.to_converted_code(node.value)
        assign_opcode = right_opcode + Opcodes.PUT + f'{ctx.memo_id}\n'.encode("utf-8")

        ctx.names[name] = [str(ctx.memo_id), None]
        ctx.converted_code.append(f"{name} = {right_str}")
        ctx.memo_id += 1
        return assign_opcode

    elif isinstance(node.targets[0], ast.Attribute):
        # 等号左侧是一个 attribute
        # eg: os.system = "whoami"
        target_attr = node.targets[0]
        if isinstance(target_attr.value, ast.Name) and target_attr.value.id in ctx.lazy_modules:
            # 属性名已经 import 并记录在 ctx.lazy_modules 里了
            # 说明是 import module 的形式
            module_name = ctx.lazy_modules[target_attr.value.id]
            attr_name = target_attr.attr
            full_name = f"{module_name}.{attr_name}"
            right_str = gen.to_converted_code(node.value)

            if full_name not in ctx.names:
                # 如果没有 import，就 import
                import_node = ast.ImportFrom(
                    module=module_name,
                    names=[ast.alias(name=attr_name, asname=None)],
                    level=0,
                )
                ctx.queue_prefix_opcode(gen.emit(import_node))
                ctx.has_transformation = True

            right_opcode = gen.emit(node.value)
            assign_opcode = right_opcode + Opcodes.PUT + f'{ctx.memo_id}\n'.encode("utf-8")

            ctx.names[full_name] = [str(ctx.memo_id), None]
            ctx.names[attr_name] = [str(ctx.memo_id), None]
            ctx.converted_code.append(f"{attr_name} = {right_str}")
            ctx.memo_id += 1
            return assign_opcode

        else:
            # 非模块的 attribute 赋值
            # eg. os.path.sep = "/"
            # 这里的 os.path 就是不是模块
            attr_name = target_attr.attr

            def _by_build() -> bytes:
                # 利用 opcode BUILD 来模拟 setattr
                left_opcode = gen.emit(target_attr.value)
                left_str = gen.to_converted_code(target_attr.value)
                right_opcode = gen.emit(node.value)
                right_str = gen.to_converted_code(node.value)
                assign_opcode = b'{left_opcode}' + Opcodes.MARK + Opcodes.NONE + Opcodes.EMPTY_DICT + b'V{attr}\n{right_opcode}' + Opcodes.SETITEM + Opcodes.TUPLE + Opcodes.BUILD
                assign_opcode = assign_opcode \
                                .replace(b'{left_opcode}', left_opcode) \
                                .replace(b'{attr}', attr_name.encode()) \
                                .replace(b'{right_opcode}', right_opcode)
                ctx.converted_code.append(f"{left_str}.{attr_name} = {right_str}")
                return assign_opcode

            def _by_setattr() -> bytes:
                # 使用 setattr(obj, attr, val)
                ctx.has_transformation = True
                call_node = ast.Call(
                    func=ast.Name(id="setattr", ctx=ast.Load()),
                    args=[
                        target_attr.value,
                        ast.Constant(value=attr_name),
                        node.value,
                    ],
                    keywords=[],
                )
                assign_opcode = gen.emit(call_node)
                ctx.converted_code.append(gen.to_converted_code(call_node))
                return assign_opcode

            return gen.generate_with_firewall(
                {
                    Opcodes.BUILD: _by_build,
                    "setattr": _by_setattr,
                },
                node=node,
            )

    elif isinstance(node.targets[0], ast.Subscript):
        # eg: a["test"] = ...
        target_sub = node.targets[0]
        slice_node = target_sub.slice
        if isinstance(slice_node, ast.Index):
            slice_node = getattr(slice_node, 'value')

        def _by_setitems() -> bytes:
            outside_str = gen.to_converted_code(target_sub.value)
            outside_opcode = gen.emit(target_sub.value)
            inside_opcode = gen.emit(slice_node)
            inside_str = gen.to_converted_code(slice_node)
            right_opcode = gen.emit(node.value)
            right_str = gen.to_converted_code(node.value)

            # 利用 opcode SETITEMS 来模拟 __setitem__
            assign_opcode = b'{outside_opcode}' + Opcodes.MARK + b'{inside_opcode}{right_opcode}' + Opcodes.SETITEMS
            assign_opcode = assign_opcode \
                            .replace(b'{outside_opcode}', outside_opcode) \
                            .replace(b'{inside_opcode}', inside_opcode) \
                            .replace(b'{right_opcode}', right_opcode)
            ctx.converted_code.append(f"{outside_str}[{inside_str}] = {right_str}")
            return assign_opcode

        def _by_magic_setitem() -> bytes:
            # 使用 getattr(obj, "__setitem__")(key, val)
            ctx.has_transformation = True
            call_node = ast.Call(
                func=ast.Call(
                    func=ast.Name(id="getattr", ctx=ast.Load()),
                    args=[
                        target_sub.value,
                        ast.Constant(value="__setitem__"),
                    ],
                    keywords=[],
                ),
                args=[slice_node, node.value],
                keywords=[],
            )
            assign_opcode = gen.emit(call_node)
            ctx.converted_code.append(gen.to_converted_code(call_node))
            return assign_opcode

        return gen.generate_with_firewall(
            {
                Opcodes.SETITEMS: _by_setitems,
                "__setitem__": _by_magic_setitem,
            },
            node=node,
        )

    else:
        raise RuntimeError(
            put_color("this complex assignment is not supported yet: ", "red") +
            f"{put_color(node.targets[0].__class__, 'cyan')} in the left part of {ctx.code}"
        )
