import ast
import pickletools

def value_type_map(v):
    vmap = {
        (int, float): 'I',
        str: 'V',
    }
    for _type in vmap:
        if isinstance(v, _type):
            return vmap[_type]

    raise RuntimeError(f'value: {v} is unknown type')


class Parser(ast.NodeVisitor):
    def __init__(self):
        self.direct_import = []
        self.memo = []
        self.names = {}
        self.memo_id = 0

        self.final_opcode = ''

    def __str__(self):
        return "b"+repr(self.final_opcode+'.')

    def optimize(self):
        return pickletools.optimize((self.final_opcode+'.').encode('utf-8'))

    # def visit_Import(self, node):
    #     # import system
    #     self.direct_import.append(node.module)

    def visit_ImportFrom(self, node):
        # from os import system
        # from os import system as sys
        def _generate_opcode():
            for _name in node.names:
                name = _name.asname or _name.name
                self.names[name] = str(self.memo_id)
                self.final_opcode += f'c{node.module}\n{name}\np{self.memo_id}\n'
                self.memo.append(name)
                self.memo_id += 1
                # print(node.module, name)

        _generate_opcode()

    def visit_Assign(self, node):
        # 赋值
        # a = "whoami"
        def _generate_opcode():
            if isinstance(node.targets[0], ast.Tuple) or isinstance(node.value, ast.Tuple):
                raise RuntimeError(
                    f"暂不支持批量赋值，请拆开写"
                )

            name = node.targets[0].id
            value = node.value.value

            self.final_opcode += f'{value_type_map(value)}{value}\np{self.memo_id}\n'
            self.names[name] = str(self.memo_id)
            self.memo.append(name)
            self.memo_id += 1

        _generate_opcode()

    def visit_Call(self, node):
        # 函数调用
        def _generate_opcode():
            func_name = node.func.id
            if self.memo[-1] == func_name:
                # 要执行的函数就在栈顶
                pass
            else:
                loc = self.names.get(func_name, None)
                if loc is None:
                    # 说明之前没有导入这个函数
                    raise RuntimeError(
                        f"函数 {func_name} 没有导入！"
                    )
                else:
                    # 之前导入过但是不在栈里
                    # g 进来
                    self.final_opcode += f'g{loc}\n'

            self.final_opcode += f'('
            for arg in node.args:
                if isinstance(arg, ast.Name):
                    # 参数是变量
                    name = arg.id
                    loc = self.names.get(name, None)
                    if loc is None:
                        # 说明之前没有定义这个变量
                        raise RuntimeError(
                            f"变量 {func_name} 没有定义！"
                        )
                    else:
                        # g 进来
                        self.final_opcode += f'g{loc}\n'
                elif isinstance(arg, ast.Constant):
                    print(dir(arg))
                    value = arg.value
                    self.final_opcode += f'{value_type_map(value)}{value}\n'

                else:
                    raise RuntimeError(
                        f"暂不支持的参数类型！{arg.__class__.__name__}"
                    )

            self.final_opcode += f'tR'

        _generate_opcode()


root = ast.parse(open('source-code.py').read())
p = Parser()
p.visit(root)
print(p)
