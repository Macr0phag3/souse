import os
import ast
import pickle
import argparse
import pickletools

from colorama import Fore, Style, init as Init


def put_color(string, color, bold=True):
    '''
    give me some color to see :P
    '''

    if color == 'gray':
        COLOR = Style.DIM+Fore.WHITE
    else:
        COLOR = getattr(Fore, color.upper(), "WHITE")

    return f'{Style.BRIGHT if bold else ""}{COLOR}{str(string)}{Style.RESET_ALL}'


def value_type_map(value):
    vmap = {
        (int, float): 'I',
        str: 'V',
    }
    for _type in vmap:
        if isinstance(value, _type):
            return vmap[_type]

    raise RuntimeError(f'value: {value} is unknown type')


class Visitor(ast.NodeVisitor):
    def __init__(self):
        self.stack = []  # 模拟 stack
        self.names = {}  # 变量记录
        self.memo_id = 0  # memo 的顶层 id

        self.final_opcode = ''

    def souse(self):
        self.result = (self.final_opcode+'.').encode('utf-8')

    def check(self):
        return pickle.loads(self.result)

    def optimize(self):
        return pickletools.optimize(self.result)

    def _find_var(self, key, tip="变量"):
        loc = self.names.get(key, None)
        if loc is None:
            # 说明之前没有定义这个变量
            raise RuntimeError(
                f"{tip} {key} 没有定义！"
            )
        else:
            # g 进来
            return loc

    def _parse_constant(self, node):
        value = node.value
        opcode = f'{value_type_map(value)}{value}'
        self.stack.append(opcode)
        return f'{opcode}\n'

    def _parse_name(self, node):
        memo_name = self._find_var(node.id)
        opcode = f'g{memo_name}\n'
        self.stack.append(memo_name)
        return opcode

    def _parse_attribute(self, node):
        targets = node.value
        attr = node.attr

        if isinstance(targets, ast.Name):
            # eg: from requests import get
            #     get.a = 1
            # eg: from fake_module import A
            #     A.a = 1  # A is 'mappingproxy' object

            opcode = self._parse_name(targets)
            return opcode, attr
            # module, name = self.import_from.get(name, [None, ]*2)
            # return f'(N}}V{attr}\n{opcode}\nstb'
        else:
            raise RuntimeError(
                f"暂不支持此点号运算符：{self.code}"
            )

    def _parse_subscript(self, node):
        # 先分析 [] 里面
        if isinstance(node.slice, ast.Index):
            # 兼容 py < 3.9
            node.slice = node.slice.value

        if isinstance(node.slice, ast.Name):
            # eg: a[b]
            inside_opcode = self._parse_name(node.slice)

        elif isinstance(node.slice, ast.Constant):
            # eg: a["1"]
            inside_opcode = self._parse_constant(node.slice)
            if not inside_opcode.startswith("V"):
                # 说明不为字典的 index
                raise RuntimeError(
                    f"暂时只支持对字典类型进行索引操作：{self.code}"
                )

        else:
            raise RuntimeError(
                f"暂时不支持这种索引：{self.code}"
            )

        # 再分析 [] 外面
        if isinstance(node.value, ast.Name):
            # eg: a[b]
            outside_opcode = self._parse_name(node.value)

        elif isinstance(node.value, ast.Call):
            outside_opcode = self._parse_call(node.value)

        else:
            raise RuntimeError(
                f"暂不支持对此种写法进行索引操作：{self.code}"
            )

        return outside_opcode, inside_opcode

    def _parse_call(self, node):
        opcode = ""
        if not isinstance(node.func, ast.Name):
            # eg: from sys import modules
            #     a = modules.get("os")
            raise RuntimeError(
                f"暂不支持对此种写法进行函数调用：{self.code}"
            )

        memo_name = self._find_var(node.func.id, tip="函数")
        if self.stack and self.stack[-1] == memo_name:
            # 要执行的函数就在栈顶
            pass
        else:
            opcode += f'g{memo_name}\n'
            self.stack.append(memo_name)

        opcode += '('
        for arg in node.args:
            if isinstance(arg, ast.Name):
                # 参数是变量
                opcode += self._parse_name(arg)

            elif isinstance(arg, ast.Constant):
                opcode += self._parse_constant(arg)

            else:
                raise RuntimeError(
                    f"暂不支持的参数类型！{arg.__class__.__name__}"
                )

        opcode += 'tR'
        return opcode

    def visit_Import(self, node):
        # eg: import os

        for _name in node.names:
            name = _name.name
            asname = f'as {_name.asname}' if _name.asname else ''

            raise RuntimeError(
                f"请使用 from {name} import xxx {asname}"
            )

    def visit_ImportFrom(self, node):
        # eg: from os import system
        # eg: from os import system as sys
        def _generate_opcode():
            for _name in node.names:
                name = _name.asname or _name.name
                self.names[name] = str(self.memo_id)
                # self.import_from[name] = [node.module, name]
                self.final_opcode += f'c{node.module}\n{name}\np{self.memo_id}\n'
                self.stack.append(str(self.memo_id))
                self.memo_id += 1

        _generate_opcode()

    def visit_Assign(self, node):
        # 赋值
        # a = "whoami"
        def _generate_opcode():
            if isinstance(node.targets[0], ast.Tuple) or isinstance(node.value, ast.Tuple):
                raise RuntimeError(
                    "暂不支持批量赋值，请拆开写"
                )

            # 先分析等号左边
            if isinstance(node.targets[0], ast.Name):
                # eg: a = ...
                name = node.targets[0].id
                assign_opcode = f'{{right_opcode}}p{self.memo_id}\n'
                self.names[name] = str(self.memo_id)
                self.stack.append(str(self.memo_id))
                self.memo_id += 1

            elif isinstance(node.targets[0], ast.Attribute):
                # 等号左边有 . 出现
                left_opcode, attr = self._parse_attribute(node.targets[0])
                assign_opcode = f'{left_opcode}(N}}}}V{attr}\n{{right_opcode}}stb'

            elif isinstance(node.targets[0], ast.Subscript):
                # eg: a["test"] = ...
                outside_opcode, inside_opcode = self._parse_subscript(
                    node.targets[0]
                )
                assign_opcode = f'{outside_opcode}({inside_opcode}{{right_opcode}}u'
            else:
                raise RuntimeError(
                    f"暂不支持此赋值语句: {self.code}, {node.targets[0].__class__}"
                )

            # 再分析等号右边
            if isinstance(node.value, ast.Name):
                # eg: ... = a
                right_opcode = self._parse_name(node.value)

            elif isinstance(node.value, ast.Constant):
                # eg: ... = 1
                right_opcode = self._parse_constant(node.value)

            elif isinstance(node.value, ast.Call):
                # eg: a = builtins.globals()
                right_opcode = self._parse_call(node.value)

            else:
                raise RuntimeError(
                    f"暂不支持此赋值语句：{self.code}"
                )

            self.final_opcode += assign_opcode.format(
                right_opcode=right_opcode)

        self.code = "\n".join(
            source_code.split('\n')
            [node.lineno-1:node.end_lineno]
        )
        _generate_opcode()

    def visit_Call(self, node):
        # 函数调用
        def _generate_opcode():
            self.final_opcode += self._parse_call(node)

        self.code = "\n".join(
            source_code.split('\n')
            [node.lineno-1:node.end_lineno]
        )
        _generate_opcode()


Init()
VERSION = '1.1'


print(
    f'''
  ██████  ▒█████   █    ██   ██████ ▓█████ 
▒██    ▒ ▒██▒  ██▒ ██  ▓██▒▒██    ▒ ▓█   ▀ 
░ ▓██▄   ▒██░  ██▒▓██  ▒██░░ ▓██▄   ▒███   
  ▒   ██▒▒██   ██░▓▓█  ░██░  ▒   ██▒▒▓█  ▄ 
▒██████▒▒░ ████▓▒░▒▒█████▓ ▒██████▒▒░▒████▒
▒ ▒▓▒ ▒ ░░ ▒░▒░▒░ ░▒▓▒ ▒ ▒ ▒ ▒▓▒ ▒ ░░░ ▒░ ░
░ ░▒  ░ ░  ░ ▒ ▒░ ░░▒░ ░ ░ ░ ░▒  ░ ░ ░ ░  ░
░  ░  ░  ░ ░ ░ ▒   ░░░ ░ ░ ░  ░  ░     ░   
      ░      ░ ░     ░           ░     ░  ░ v{Fore.GREEN}{VERSION}{Style.RESET_ALL}
'''
    .replace('█', put_color('█', "yellow"))
    .replace('▒', put_color('▒', "yellow", bold=False))
    .replace('▓', put_color('▓', "yellow"))
    .replace('░', put_color('░', "white", bold=False))
    .replace('▀', put_color('▀', "yellow"))
    .replace('▄', put_color('▄', "yellow"))
)

parser = argparse.ArgumentParser(description=f'Version: {VERSION}; Running in Py3.x')
parser.add_argument(
    "--check", action="store_true",
    help="run pickle.loads() to test opcode"
)
parser.add_argument(
    "--no-optimize", action="store_false",
    help="do NOT optimize opcode"
)
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("-f", "--filename", help=".py source code filename")
group.add_argument(
    "--run-test", action="store_true",
    help="run test with test/^[^N]*.py"
)

args = parser.parse_args()

need_check = args.check
need_optimize = args.no_optimize
run_test = args.run_test

if run_test:
    # 代码质量测试模式下
    # 不优化 opcode
    # 不执行 opcode
    need_optimize = False
    need_check = False
    filenames = [
        "./test/"+i for i in list(os.walk("./test"))[0][2]
        if not i.startswith("N-")
    ]
else:
    filenames = [args.filename]

print(f'[*] need check: {put_color(need_check, ["white", "green"][int(need_check)])}')
print(f'[*] need optimize: {put_color(need_optimize, ["white", "green"][int(need_optimize)])}')

for filename in filenames:
    tip = lambda c: f'[+] input: {put_color(filename, c)}'  # noqa: E731
    try:
        source_code = open(filename).read()
        root = ast.parse(source_code)
        visitor = Visitor()
        visitor.visit(root)
        visitor.souse()
    except Exception:
        print(tip("red"), end="\n\n")
        raise
    else:
        if run_test:
            answer = [
                i.replace("# ", "").strip()
                for i in open(filename).readlines() if i.strip()
            ][-1]
            correct = answer == str(visitor.result)
            if correct:
                print(tip("green"))
                continue
            else:
                print(tip("yellow"))
        else:
            print(tip("green"))

    print(f'  [-] raw opcode:       {put_color(visitor.result, "green")}')

    if need_optimize:
        print(f'  [-] optimized opcode: {put_color(visitor.optimize(), "green")}')

    if need_check:
        print(f'  [-] opcode test result: {put_color(visitor.check(), "white")}')

    if run_test:
        loc = [
            (i, j)
            for i, j in zip(enumerate(str(visitor.result)), enumerate(answer))
            if i[1] != j[1]
        ][0][0][0]
        answer = (
            put_color(answer[:loc], "green") +
            put_color(answer[loc:-1], "yellow") +
            put_color(answer[-1], "green")
        )
        print(f'  [-] answer for test:  {answer}')

print("\n[*] done")
