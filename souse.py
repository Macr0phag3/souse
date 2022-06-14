import os
import ast
import json
import pickle
import struct
import argparse
import functools
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


def format_opcode(code, value):
    def _pure(value):
        return repr(value.strip())[2:-1] if isinstance(value, bytes) else value.strip()

    def _format(code, value='', return_value=False):
        if code == b"S":
            return f"S'{value}'\n".encode('utf-8')

        elif code == b"J":
            # limit: -2147483648 <= value <= 2147483647
            value = struct.pack('i0i', value)

        if not isinstance(value, bytes):
            value = str(value).encode('utf-8')
            if value:
                value += b"\n"

        if return_value:
            return _pure(value), code + value

        return code + value

    code = code if isinstance(code, list) else [code]
    if not bypass:
        # 不需要 bypass
        return _format(code[0], value)

    pure_code = [_pure(i) for i in code]

    related_rules = {
        k: v for k, v in firewall_rules.items()
        if k in pure_code and v in [str(value), "*"]
    }
    if not related_rules:
        # 不需要 bypass
        return _format(code[0], value)

    if rule_type == 'black':
        for i, v in enumerate(pure_code):
            for _c, _v in related_rules.items():
                if _v == "*":
                    if _c != v:
                        # 直接换掉
                        print(
                            f"[*] choice {put_color(v, 'blue')} "
                            # f"instead of {put_color(pure_code[0], 'white')} "
                            f"to bypass rule: {put_color({_c: _v}, 'white')}"
                        )
                        return _format(code[i], value)

                elif _v == str(value):
                    # 替换 value
                    try:
                        new_v, bypassed = _format(
                            code[i], value, return_value=True)
                    except struct.error as e:
                        pass

                    else:
                        if _v != new_v:
                            print(
                                f"[*] choice {put_color(v, 'blue')} "
                                # f"instead of {put_color(pure_code[0], 'white')} "
                                f"to bypass rule: {put_color({_c: _v}, 'white')}"
                            )
                            return bypassed

        # 均失败
        raise RuntimeError(
            f"can NOT bypass: {put_color(related_rules, 'white')}, "
            f"must use opcode in {put_color(pure_code, 'white')}"
        )


def value_type_map(value):
    vmap = {
        int: [b'I', b'J'],
        float: b'F',
        str: [b'V', b'S'],
    }
    cmap = {
        None: b'N',
        True: [b'I01\n', b'\x88'],
        False: [b'I00\n', b'\x89'],
    }
    for _type in vmap:
        if type(value) is _type:
            v = vmap[_type]
            return format_opcode(v, value)

    v = cmap.get(value, None)
    if v is None:
        raise RuntimeError(
            put_color('this basic type is not supported yet :', 'red') +
            f"{put_color(value, 'cyan')} in {self.code}, "
            f"type is {put_color(type(value), 'cyan')}"
        )
    else:
        return format_opcode(v, "")


def transfer_funcs(func_name):
    name = {
        "b64": "base64_encode",
        "base64": "base64_encode",
        "base64encode": "base64_encode",

        "hex": "hex_encode",
        "hexencode": "hex_encode",

        "url": "url_decode",
        "urldecode": "url_decode",
    }.get(func_name, func_name)

    return {
        'base64_encode': __import__('base64').b64encode,
        'hex_encode': functools.partial(__import__('codecs').encode, encoding="hex"),
        'url_decode': __import__('urllib.parse', fromlist=[""]).quote_plus,
    }.get(
        name,
        lambda x: put_color(
            f"no such transfer function: {put_color(func_name, 'blue')}",
            "yellow"
        )
    )


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

    def _find_var(self, key):
        loc = self.names.get(key, None)
        if loc is None:
            # 说明之前没有定义这个变量
            raise RuntimeError(
                put_color("this var is not defined: ", "red") +
                f'{put_color(key, "cyan")} in {self.code}'
            )
        else:
            # g 进来
            return loc

    def _flat(self, node):
        if isinstance(node, ast.Constant):
            return value_type_map(node.value)

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
                put_color("this struct is not supported yet: ", "red") +
                f'{put_color(node.__class__, "cyan")} in {self.code}'
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
                put_color("this complex dot operators(.) is not supported yet: ", "red") +
                f'{put_color(targets.__class__, "cyan")} in {self.code}'
            )

    def _parse_subscript(self, node):
        # 先分析 [] 里面
        if isinstance(node.slice, ast.Index):
            # 兼容 py < 3.9
            node.slice = node.slice.value

        if isinstance(node.slice, ast.Subscript):
            raise RuntimeError(
                put_color("this nested index is not supported yet: ") +
                f'{put_color(node.slice.__class__, "cyan")} in {self.code}'
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
                    put_color("this function call is not supported yet: ", "red") +
                    f'{put_color(node.func.__class__, "cyan")} in {self.code}'
                )

        # 获取函数名
        # eg: from sys import modules
        #     a = modules.get("os")
        func_name = self._flat(node.func)
        return func_name + b"".join(opcode[::-1])

    def visit_Import(self, node):
        # eg: import os
        self.code = put_color("\n".join(
            source_code.split('\n')
            [node.lineno-1: node.end_lineno]
        ), "white")

        for _name in node.names:
            name = _name.name
            asname = f' as {_name.asname}' if _name.asname else ''

            raise RuntimeError(
                put_color("direct import is not supported yet: ", "red") +
                f"{self.code}, "
                "use " +
                put_color(f"from {name} import xxx{asname}", "cyan") +
                " instead!"
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

        def _generate_opcode():
            if isinstance(node.targets[0], ast.Tuple):
                raise RuntimeError(
                    put_color("mass assignment is not supported yet: ", "red") +
                    f"{self.code}, unpack it!"
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
                    put_color("this complex assignment is not supported yet: ", "red") +
                    f"{put_color(node.targets[0].__class__, 'cyan')} in the left part of {self.code}"
                )

            # 再分析等号右边
            # eg: ... = a -> isinstance(node.value, ast.Name)
            # eg: ... = 1 -> isinstance(node.value, ast.Constant)
            # eg: a = builtins.globals() -> isinstance(node.value, ast.Call)
            right_opcode = self._flat(node.value)
            self.final_opcode += assign_opcode.replace(
                b"{right_opcode}", right_opcode
            )

        self.code = put_color("\n".join(
            source_code.split('\n')
            [node.lineno-1: node.end_lineno]
        ), "white")
        _generate_opcode()

    def visit_Call(self, node):
        # 函数调用
        def _generate_opcode():
            self.final_opcode += self._flat(node)

        self.code = put_color("\n".join(
            source_code.split('\n')
            [node.lineno-1:node.end_lineno]
        ), "white")
        _generate_opcode()


Init()
VERSION = '2.1'


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
    help="run test with test/*.py (not startswith `N-`)"
)
parser.add_argument(
    "-p", "--bypass", default=False,
    help="try bypass limitation"
)
parser.add_argument(
    "-t", "--transfer", default=None,
    help="transfer result(eg. base64encode)"
)

args = parser.parse_args()

need_check = args.check
need_optimize = args.no_optimize
run_test = args.run_test
transfer = args.transfer
transfer_func = transfer_funcs(transfer)

if run_test:
    # 代码质量测试模式下
    # 不优化 opcode、不执行 opcode、不 bypass
    need_optimize = False
    need_check = False
    bypass = False
    directory = "./test/"
    filenames = sorted([
        directory+i for i in list(os.walk(directory))[0][2]
        if not i.startswith("N-")
    ])
else:
    filenames = [args.filename]

print(f'[*] need check:        {put_color(need_check, ["gray", "green"][int(need_check)])}')
print(f'[*] need optimize:     {put_color(need_optimize, ["gray", "green"][int(need_optimize)])}')

firewall_rules = {}
bypass = False
if args.bypass:
    try:
        firewalls = json.load(open(args.bypass))
    except Exception as e:
        print("\n[!]", put_color(f"{args.bypass} has invalid bypass rules: {e}\n", 'yellow'))
    else:
        rule_type = firewalls.get("type", None)
        if rule_type not in ["black", "white"]:
            print("\n[!]", put_color(f'{args.bypass} must contains a json key: `type` in `["black", "white"]`\n', "yellow"))
        else:
            firewall_rules = firewalls.get('rules', {})

            if not firewall_rules:
                print("\n[!]", put_color(f"{args.bypass} has no rules\n", 'yellow'))
            else:
                bypass = True

print(f'[*] try bypass:        {put_color(args.bypass, ["gray", "cyan"][int(bypass)])}')
print(f'[*] transfer function: {put_color(transfer, ["blue", "gray"][bool(bypass)])}\n')
for filename in filenames:
    def tip(c): return f'[+] input: {put_color(filename, c)}'
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
            print(tip("cyan"))

    print(f'  [-] raw opcode:         {put_color(visitor.result, "green")}')

    if need_optimize:
        print(f'  [-] optimized opcode:   {put_color(visitor.optimize(), "green")}')

        if transfer:
            print(f'  [-] transfered opcode:  {put_color(transfer_func(visitor.optimize()), "green")}')

    elif transfer:
        print(f'  [-] transfered opcode:  {put_color(transfer_func(visitor.result), "green")}')

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
