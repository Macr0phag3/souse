import ast


def generate(gen, node: ast.UnaryOp) -> bytes:
    if not isinstance(node.op, ast.USub) or not isinstance(node.operand, ast.Constant) or not isinstance(node.operand.value, (int, float)):
        gen.ctx._error(node, f"this unary op is not supported yet: {node.op.__class__.__name__}")

    # 移除 - 之后，把值直接扔回给生成器继续生成
    value = -node.operand.value
    new_node = ast.Constant(value=value)
    return gen.emit(new_node)
