import ast


def generate(gen, node: ast.Slice) -> bytes:
    """
    目前 slice 无法通过 opcode 直接构造
    只能通过 slice(lower, upper, step) 来间接构造
    """
    gen.ctx.has_transformation = True

    call_node = ast.Call(
        func=ast.Name(id="slice", ctx=ast.Load()),
        args=[
            node.lower if node.lower else ast.Constant(value=None),
            node.upper if node.upper else ast.Constant(value=None),
            node.step if node.step else ast.Constant(value=None),
        ],
        keywords=[],
    )
    return gen.emit(call_node)
