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
        # self.direct_import = []
        self.memo = []
        self.names = {}
        self.memo_id = 0

        self.final_opcode = ''

    def __str__(self):
        return "b"+repr(self.final_opcode+'.')

    def optimize(self):
        return pickletools.optimize((self.final_opcode+'.').encode('utf-8'))

    def find_var(self, key, tip="变量"):
        loc = self.names.get(key, None)
        if loc is None:
            # 说明之前没有定义这个变量
            raise RuntimeError(
                f"{tip} {key} 没有定义！"
            )
        else:
            # g 进来
            return loc

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
                    "暂不支持批量赋值，请拆开写"
                )

            if isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                if isinstance(node.value, ast.Constant):
                    # eg: a = 1
                    value = node.value.value

                    self.final_opcode += f'{value_type_map(value)}{value}\np{self.memo_id}\n'
                    self.names[name] = str(self.memo_id)
                    self.memo.append(name)
                    self.memo_id += 1
                elif isinstance(node.value, ast.Call):
                    # eg: a = builtins.globals()
                    self.visit_Call(node.value)
                else:
                    raise RuntimeError(
                        f"暂不支持此赋值语句：{code}"
                    )

            elif isinstance(node.targets[0], ast.Attribute):
                targets = node.targets[0].value
                attr = node.targets[0].attr

                if isinstance(node.value, ast.Name):
                    # eg: ... = a
                    name = node.value.id
                    value = f'g{self.find_var(name)}'

                elif isinstance(node.value, ast.Constant):
                    # eg: ... = 1
                    value = f'V{node.value.value}'

                else:
                    raise RuntimeError(
                        f"暂不支持此赋值语句：{code}"
                    )

                if isinstance(targets, ast.Attribute):
                    func_name = targets.attr
                    if isinstance(targets.value, ast.Name):
                        # eg: requests.get.a = ...
                        module = targets.value.id
                        self.final_opcode += f'c{module}\n{func_name}\n}}V{attr}\n{value}\nsb'
                    else:
                        # eg: requests.get.a.a = ...
                        raise RuntimeError(
                            f"暂不支持此赋值语句：{code}"
                        )

                elif isinstance(targets, ast.Name):
                    # eg: requests.a = 1

                    # module = targets.id
                    # self.final_opcode += f'c{module}\n__dict__\n(N}}V{attr}\n{value}\ntsb'
                    raise RuntimeError(
                        f"暂不支持此赋值语句：{code}"
                    )
                else:
                    raise RuntimeError(
                        f"暂不支持此赋值语句：{code}"
                    )
            elif isinstance(node.targets[0], ast.Subscript):
                # eg: a["test"] = ...
                _slice = node.targets[0].slice
                print(dir(node.targets[0]), _slice.value)
            else:
                raise RuntimeError(
                    f"暂不支持此赋值语句: {code}, {node.targets[0].__class__}"
                )

        code = "\n".join(source_code.split('\n')[node.lineno-1:node.end_lineno])
        _generate_opcode()

    def visit_Call(self, node):
        # 函数调用
        def _generate_opcode():
            func_name = node.func.id
            if self.memo and self.memo[-1] == func_name:
                # 要执行的函数就在栈顶
                pass
            else:
                self.final_opcode += f'g{self.find_var(func_name, tip="函数")}\n'

            self.final_opcode += '('
            for arg in node.args:
                if isinstance(arg, ast.Name):
                    # 参数是变量
                    name = arg.id
                    self.final_opcode += f'g{self.find_var(name)}\n'

                elif isinstance(arg, ast.Constant):
                    print(dir(arg))
                    value = arg.value
                    self.final_opcode += f'{value_type_map(value)}{value}\n'

                else:
                    raise RuntimeError(
                        f"暂不支持的参数类型！{arg.__class__.__name__}"
                    )

            self.final_opcode += 'tR'

        _generate_opcode()

    def visit_Attribute(self, node):
        # 属性访问
        def _generate_opcode():
            pass

        print(node)
        _generate_opcode()

    def visit_Subscript(self, node):
        # 下标访问
        def _generate_opcode():
            pass

        print(node)
        _generate_opcode()


source_code = open('source-code.py').read()
root = ast.parse(source_code)
p = Parser()
p.visit(root)
print(p)
