import ast


def generate(gen, node: ast.Subscript) -> bytes:
    """
    目前 subscript 无法通过 opcode 直接构造
    只能通过 getattr(obj, "__getitem__")(key) 来间接构造
    直接扔回给生成器继续生成
    """
    # 转换 obj[key] -> getattr(obj, "__getitem__")(key)
    gen.ctx.has_transformation = True

    slice_node = node.slice
    if isinstance(slice_node, ast.Index):
        # 兼容 py < 3.9
        slice_node = getattr(slice_node, 'value')

    getattr_call = ast.Call(
        func=ast.Name(id="getattr", ctx=ast.Load()),
        args=[node.value, ast.Constant(value="__getitem__")],
        keywords=[],
    )
    call_node = ast.Call(
        func=getattr_call,
        args=[slice_node],
        keywords=[],
    )
    return gen.emit(call_node)
