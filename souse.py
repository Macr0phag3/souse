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
        int: f'I',
        float: f'F',
        str: f'V',
    }
    cmap = {
        None: 'N',
        True: 'I01\n',
        False: 'I00\n',
    }
    for _type in vmap:
        if type(value) is _type:
            return f'{vmap[_type]}{value}\n'

    v = cmap.get(value, None)
    if v is None:
        raise RuntimeError(f'value: {value} is unknown type')
    else:
        return v


class Visitor(ast.NodeVisitor):
    def __init__(self):
        self.names = {}  # 变量记录
        self.memo_id = 0  # memo 的顶层 id

        self.final_opcode = b''

    def souse(self):
        self.result = self.final_opcode+b'.'

    def check(self):
        return pickle.loads(self.result)

    def optimize(self):
        optimized = []
        result = pickletools.optimize(self.result).split(b'\n')
        memo_g_ids = [i for i in result if i.startswith(b"g")]
        while result:
            optimized.append(result.pop(0))

            if (
                len(optimized) > 2 and
                optimized[-2].startswith(b"p") and
                optimized[-1].startswith(b"g") and
                optimized[-1][1:] == optimized[-2][1:] and
                memo_g_ids.count(optimized[-1]) == 1
            ):
                # 优化掉
                optimized.pop()

        return pickletools.optimize(b'\n'.join(optimized))

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

    def _flat(self, node):
        if isinstance(node, ast.Constant):
            return value_type_map(node.value).encode('utf-8')

        elif isinstance(node, ast.Set):
            # PVM Protocol 4
            return (
                b'\x8f(' +
                b"".join([self._flat(elt) for elt in node.elts]) +
                b'\x90'
            )

        elif isinstance(node, ast.List):
            return (
                b'(' +
                b"".join([self._flat(elt) for elt in node.elts]) +
                b'l'
            )

        elif isinstance(node, ast.Tuple):
            return (
                b'(' +
                b"".join([self._flat(elt) for elt in node.elts]) +
                b't'
            )

        elif isinstance(node, ast.Dict):
            return (
                b'(' +
                b"".join([self._flat(k) + self._flat(v) for k, v in zip(node.keys, node.values)]) +
                b'd'
            )

        elif isinstance(node, ast.Name):
            memo_name = self._find_var(node.id)
            return f'g{memo_name}\n'.encode('utf-8')

        elif isinstance(node, ast.Call):
            return self._parse_call(node)

        elif isinstance(node, ast.Subscript):
            return self._parse_subscript(node)

        else:
            raise RuntimeError(
                f"暂不支持此数据结构：{node.__class__}"
            )

    def _parse_attribute(self, node):
        targets = node.value
        attr = node.attr

        if isinstance(targets, ast.Name):
            # eg: from requests import get
            #     get.a = 1
            # eg: from fake_module import A
            #     A.a = 1  # A is 'mappingproxy' object

            opcode = self._flat(targets)
            return opcode, attr.encode("utf-8")
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

        if isinstance(node.slice, ast.Subscript):
            raise RuntimeError(
                f"暂不支持索引嵌套：{node.__class__}"
            )

        inside_opcode = self._flat(node.slice)

        # 再分析 [] 外面
        outside_opcode = self._flat(node.value)
        return outside_opcode, inside_opcode

    def _parse_call(self, node):
        opcode = []
        while True:
            opcode.append(
                b"(" + b"".join([self._flat(arg) for arg in node.args]) + b"tR"
            )
            if isinstance(node.func, ast.Name):
                break

            elif isinstance(node.func, ast.Call):
                node = node.func
                continue
            else:
                raise RuntimeError(
                    f"暂不支持对此种写法进行函数调用：{self.code}, {node.func.__class__}"
                )

        # 获取函数名
        # eg: from sys import modules
        #     a = modules.get("os")
        memo_name = self._find_var(node.func.id, tip="函数")
        func_name = self._flat(node.func)
        return func_name + b"".join(opcode[::-1])

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
                self.final_opcode += f'c{node.module}\n{name}\np{self.memo_id}\n'.encode('utf-8')
                self.memo_id += 1

        _generate_opcode()

    def visit_Assign(self, node):
        # 赋值
        # a = "whoami"
        def _raise(tip):
            raise RuntimeError(
                f"{tip}：{self.code}, {node.value.__class__}"
            )

        def _generate_opcode():
            if isinstance(node.targets[0], ast.Tuple):
                raise RuntimeError(
                    "暂不支持批量赋值，请拆开写"
                )

            # 先分析等号左边
            if isinstance(node.targets[0], ast.Name):
                # eg: a = ...
                name = node.targets[0].id
                assign_opcode = b'{right_opcode}p{self.memo_id}\n' \
                                .replace(b'{self.memo_id}', str(self.memo_id).encode("utf-8"))

                self.names[name] = str(self.memo_id)
                self.memo_id += 1

            elif isinstance(node.targets[0], ast.Attribute):
                # 等号左边有 . 出现
                left_opcode, attr = self._parse_attribute(node.targets[0])
                assign_opcode = b'{left_opcode}(N}V{attr}\n{right_opcode}stb' \
                                .replace(b'{left_opcode}', left_opcode) \
                                .replace(b'{attr}', attr)

            elif isinstance(node.targets[0], ast.Subscript):
                # eg: a["test"] = ...
                outside_opcode, inside_opcode = self._flat(
                    node.targets[0]
                )
                assign_opcode = b'{outside_opcode}({inside_opcode}{right_opcode}u' \
                                .replace(b'{outside_opcode}', outside_opcode) \
                                .replace(b'{inside_opcode}', inside_opcode)

            else:
                raise RuntimeError(
                    f"暂不支持此赋值语句的左半部分: {self.code}, {node.targets[0].__class__}"
                )

            # 再分析等号右边
            # eg: ... = a -> isinstance(node.value, ast.Name)
            # eg: ... = 1 -> isinstance(node.value, ast.Constant)
            # eg: a = builtins.globals() -> isinstance(node.value, ast.Call)
            right_opcode = self._flat(node.value)
            self.final_opcode += assign_opcode.replace(
                b"{right_opcode}", right_opcode
            )

        self.code = "\n".join(
            source_code.split('\n')
            [node.lineno-1: node.end_lineno]
        )
        _generate_opcode()

    def visit_Call(self, node):
        # 函数调用
        def _generate_opcode():
            self.final_opcode += self._flat(node)

        self.code = "\n".join(
            source_code.split('\n')
            [node.lineno-1:node.end_lineno]
        )
        _generate_opcode()


Init()
VERSION = '1.2'


(
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
    def tip(c): return f'[+] input: {put_color(filename, c)}'  # noqa: E731
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
