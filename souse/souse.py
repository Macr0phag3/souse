import os
import sys
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


def transfer_funcs(func_name):
    if not func_name:
        return lambda x: x
    func = {
        'base64_encode': __import__('base64').b64encode,
        'hex_encode': functools.partial(__import__('codecs').encode, encoding="hex"),
        'url_decode': __import__('urllib.parse', fromlist=[""]).quote_plus,
    }.get(FUNC_NAME.get(func_name, func_name), 'unknown')
    if func == 'unknown':
        raise RuntimeError(put_color(
            f"no such transfer function: {put_color(func_name, 'blue')}",
            "yellow"
        ))

    return func


class Visitor(ast.NodeVisitor):
    def __init__(self, source_code, firewall_rules):
        self.names = {}  # 变量记录
        self.memo_id = 0  # memo 的顶层 id
        self.firewall_rules = firewall_rules
        self.source_code = source_code

        self.final_opcode = b''

    def souse(self):
        self.result = self.final_opcode+b'.'

    def check(self):
        with open('.souse-result.tmp', 'w') as fw:
            fw.write(
                'import pickle\n'
                f'print(pickle.loads({repr(self.result)}), end="")\n'
            )

        return os.popen(
            f"{sys.executable} .souse-result.tmp"
        ).read()

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

    def _flat(self, node):
        '''递归处理基础的语句
        '''
        _types = {
            ast.Constant: self._parse_constant,
            ast.List: self._parse_list,
            ast.Set: self._parse_set,
            ast.Tuple: self._parse_tuple,
            ast.Dict: self._parse_dict,
            ast.Name: self._parse_name,
            ast.Call: self._parse_call,
            ast.Attribute: self._parse_attribute,
            ast.Subscript: self._parse_subscript,
        }

        for _type in _types:
            if isinstance(node, _type):
                return _types[_type](node)

        raise RuntimeError(
            put_color("this struct is not supported yet: ", "red") +
            f'{put_color(node.__class__, "cyan")} in {self.code}'
        )

    def _parse_constant(self, node):
        def __generate_int():
            code = ['I', 'J']
            related_rules = {
                k: v for k, v in self.firewall_rules.items()
                if k in code and v in [str(node.value), "*"]
            }
            if not related_rules:
                return f'{code[0]}{node.value}\n'

            bypass_code = [i for i in code if i not in related_rules]
            if not bypass_code:
                raise RuntimeError(
                    f"can NOT bypass: {put_color(related_rules, 'white')}, "
                    f"must use opcode in {put_color(code, 'white')}"
                )

            print(
                f"[*] choice {put_color(bypass_code[0], 'blue')} "
                # f"instead of {put_color(pure_code[0], 'white')} "
                f"to bypass rule: {put_color(related_rules, 'white')}"
            )

            if bypass_code[0] == 'J':
                return b"J"+struct.pack('i0i', node.value)
            else:
                raise NotImplementedError(
                    f"{put_color('BUG FOUND', 'red')}, bypass code "
                    f"{put_color(bypass_code[0], 'white')} is "
                    'not implemented'
                )

        def __generate_float():
            return f'F{node.value}\n'

        def __generate_str():
            code = ['V', 'S']
            related_rules = {
                k: v for k, v in self.firewall_rules.items()
                if k in code and v in [str(node.value), "*"]
            }
            if not related_rules:
                return f'{code[0]}{node.value}\n'

            bypass_code = [i for i in code if i not in related_rules]
            if not bypass_code:
                raise RuntimeError(
                    f"can NOT bypass: {put_color(related_rules, 'white')}, "
                    f"must use opcode in {put_color(code, 'white')}"
                )

            print(
                f"[*] choice {put_color(bypass_code[0], 'blue')} "
                f"to bypass rule: {put_color(related_rules, 'white')}"
            )
            if bypass_code[0] == 'S':
                return f"S'{node.value}'\n"
            else:
                raise NotImplementedError(
                    f"{put_color('BUG FOUND', 'red')}, bypass code "
                    f"{put_color(bypass_code[0], 'white')} is "
                    'not implemented'
                )

        def __generate_none():
            return f'N'

        def __generate_true():
            code = ['I01', '\\x88']
            related_rules = {
                k: v for k, v in self.firewall_rules.items()
                if k in code and v in ["*"]
            }
            if not related_rules:
                return f'{code[0]}\n'

            bypass_code = [i for i in code if i not in related_rules]
            if not bypass_code:
                raise RuntimeError(
                    f"can NOT bypass: {put_color(related_rules, 'white')}, "
                    f"must use opcode in {put_color(code, 'white')}"
                )

            print(
                f"[*] choice {put_color(bypass_code[0], 'blue')} "
                f"to bypass rule: {put_color(related_rules, 'white')}"
            )
            if bypass_code[0] == '\\x88':
                return b'\x88'
            else:
                raise NotImplementedError(
                    f"{put_color('BUG FOUND', 'red')}, bypass code "
                    f"{put_color(bypass_code[0], 'white')} is "
                    'not implemented'
                )
            return f'{bypass_code[0]}\n'

        def __generate_false():
            code = ['I00', '\\x89']
            related_rules = {
                k: v for k, v in self.firewall_rules.items()
                if k in code and v in ["*"]
            }
            if not related_rules:
                return f'{code[0]}\n'

            bypass_code = [i for i in code if i not in related_rules]
            if not bypass_code:
                raise RuntimeError(
                    f"can NOT bypass: {put_color(related_rules, 'white')}, "
                    f"must use opcode in {put_color(code, 'white')}"
                )

            print(
                f"[*] choice {put_color(bypass_code[0], 'blue')} "
                f"to bypass rule: {put_color(related_rules, 'white')}"
            )
            if bypass_code[0] == '\\x89':
                return b'\x89'
            else:
                raise NotImplementedError(
                    f"{put_color('BUG FOUND', 'red')}, bypass code "
                    f"{put_color(bypass_code[0], 'white')} is "
                    'not implemented'
                )
            return f'{bypass_code[0]}\n'

        value_map = {
            int: __generate_int,
            float: __generate_float,
            str: __generate_str,

            None: __generate_none,
            True: __generate_true,
            False: __generate_false,
        }
        generate_func = (
            value_map.get(type(node.value), None)
            or
            value_map.get(node.value, None)
        )
        if generate_func is None:
            raise RuntimeError(
                put_color('this basic type is not supported yet: ', 'red') +
                f"{put_color(node.value, 'cyan')} in {self.code}, "
                f"type is {put_color(type(node.value), 'cyan')}"
            )

        result = generate_func()
        if isinstance(result, str):
            result = result.encode()

        return result

    def _parse_set(self, node):
        # PVM Protocol 4
        return (
            b'\x8f(' +
            b"".join([self._flat(elt) for elt in node.elts]) +
            b'\x90'
        )

    def _parse_list(self, node):
        return (
            b'(' +
            b"".join([self._flat(elt) for elt in node.elts]) +
            b'l'
        )

    def _parse_tuple(self, node):
        return (
            b'(' +
            b"".join([self._flat(elt) for elt in node.elts]) +
            b't'
        )

    def _parse_dict(self, node):
        return (
            b'(' +
            b"".join([self._flat(k) + self._flat(v) for k, v in zip(node.keys, node.values)]) +
            b'd'
        )

    def _parse_name(self, node):
        memo_name = self.names.get(node.id, [None, None])[0]
        if memo_name is None:
            # 说明之前没有定义这个变量
            raise RuntimeError(
                put_color("this var is not defined: ", "red") +
                f'{put_color(node.id, "cyan")} in {self.code}'
            )

        return f'g{memo_name}\n'.encode('utf-8')

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
        def _normal_generate(node):
            if isinstance(node.func, ast.Name) or isinstance(node.func, ast.Call):
                opcode = (
                    b"(" + b"".join(
                        [self._flat(arg) for arg in node.args]
                    ) + b"tR"
                )
            else:
                raise RuntimeError(
                    put_color("this function call is not supported yet: ", "red") +
                    f'{put_color(node.func.__class__, "cyan")} in {self.code}'
                )

            # 获取函数名
            # eg: from sys import modules
            #     a = modules.get("os")
            func_name = self._flat(node.func)
            return func_name+opcode

        def _obj_generate(node):
            func_name = self._flat(node.func)
            if isinstance(node.func, ast.Call) or isinstance(node.func, ast.Name):
                opcode = (
                    b"(" + func_name + b"".join(
                        [self._flat(arg) for arg in node.args]
                    ) + b"o"
                )
            else:
                raise RuntimeError(
                    put_color("this function call is not supported yet: ", "red") +
                    f'{put_color(node.func.__class__, "cyan")} in {self.code}'
                )

            return opcode

        def _instance_generate(node):
            # (S'ls'\nios\nsystem\n
            func_name = self._flat(node.func)
            code, num = list(func_name.strip().decode())

            imported_func = [
                (j[1], i)
                for i, j in self.names.items()
                if j[0] == num and j[1]
            ]
            if code != 'g' or not imported_func:
                raise RuntimeError(
                    f"can NOT bypass: {put_color(related_rules, 'white')}, "
                    f"function must can be import then call: {put_color(self.code, 'white')}"
                )

            imported_func = imported_func[0]
            if isinstance(node.func, ast.Name):
                opcode = (
                    b"(" + b"".join(
                        [self._flat(arg) for arg in node.args]
                    ) + b"i" + ("\n".join(imported_func)).encode() + b"\n"
                )
            else:
                raise RuntimeError(
                    put_color("this function call is not supported yet: ", "red") +
                    f'{put_color(node.func.__class__, "cyan")} in {self.code}'
                )

            return opcode

        code = ['R', 'o', 'i']
        related_rules = {
            k: v for k, v in self.firewall_rules.items()
            if k in code and v in ["*"]
        }
        if not related_rules:
            return _normal_generate(node)

        bypass_code = [i for i in code if i not in related_rules]
        if not bypass_code:
            raise RuntimeError(
                f"can NOT bypass: {put_color(related_rules, 'white')}, "
                f"must use opcode in {put_color(code, 'white')}"
            )

        print(
            f"[*] choice {put_color(bypass_code[0], 'blue')} "
            f"to bypass rule: {put_color(related_rules, 'white')}"
        )

        if bypass_code[0] == 'o':
            return _obj_generate(node)
        elif bypass_code[0] == 'i':
            return _instance_generate(node)
        else:
            raise NotImplementedError(
                f"{put_color('BUG FOUND', 'red')}, bypass code "
                f"{put_color(bypass_code[0], 'white')} is "
                'not implemented'
            )

    def visit_Import(self, node):
        # MUST raise an Error
        # eg: import os
        self.code = put_color("\n".join(
            self.source_code.split('\n')
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
        # eg: from os import system, popen
        def _generate_opcode():
            for _name in node.names:
                name = _name.asname or _name.name
                self.names[name] = [str(self.memo_id), node.module]
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

                self.names[name] = [str(self.memo_id), None]
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
            self.source_code.split('\n')
            [node.lineno-1: node.end_lineno]
        ), "white")
        _generate_opcode()

    def visit_Call(self, node):
        # 函数调用
        def _generate_opcode():
            self.final_opcode += self._flat(node)

        self.code = put_color("\n".join(
            self.source_code.split('\n')
            [node.lineno-1:node.end_lineno]
        ), "white")
        _generate_opcode()


class API:
    def __init__(self, source_code, firewall_rules={}, optimized=True, transfer=''):
        self.source_code = source_code
        self.root = ast.parse(self.source_code)
        self.firewall_rules = firewall_rules
        self.optimized = optimized
        self.transfer = transfer

    def _generate(self):
        visitor = Visitor(
            self.source_code, self.firewall_rules
        )
        visitor.visit(self.root)
        visitor.souse()
        return visitor

    def generate(self):
        visitor = Visitor(
            self.source_code,
            self.firewall_rules,
        )
        visitor.visit(self.root)
        visitor.souse()

        result = visitor.result

        if self.optimized:
            result = visitor.optimize()

        if isinstance(self.transfer, list):
            for func in self.transfer:
                result = func(result)

            return result

        if self.transfer is None or isinstance(self.transfer, str):
            self.transfer = transfer_funcs(self.transfer)

        return self.transfer(result)


def cli():
    Init()
    print(LOGO)

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
        help=f"transfer result with: { {i for i in FUNC_NAME.values()} }"
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
        directory = os.path.join(
            *list(os.path.split(__file__)[:-1])+["test"],
        )
        filenames = sorted([
            os.path.join(directory, i) for i in list(os.walk(directory))[0][2]
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
            firewall_rules = json.load(open(args.bypass))
        except Exception as e:
            print("\n[!]", put_color(f"{args.bypass} has invalid bypass rules: {e}\n", 'yellow'))
        else:
            if not firewall_rules:
                print("\n[!]", put_color(f"{args.bypass} has no rules\n", 'yellow'))
            else:
                bypass = True

    print(f'[*] try bypass:        {put_color(args.bypass, ["gray", "cyan"][int(bypass)])}')
    print(f'[*] transfer function: {put_color(transfer, ["blue", "gray"][bool(bypass)])}\n')
    for filename in filenames:
        def tip(c): return f'[+] input: {put_color(filename, c)}'

        source_code = open(filename).read()
        try:
            visitor = API(
                source_code, firewall_rules, need_optimize,
            )._generate()
        except Exception:
            print(tip("red"), end="\n\n")
            raise
        else:
            if run_test:
                answer = [
                    i.replace("# ", "").strip()
                    for i in source_code.split('\n') if i.strip()
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
            print(f'  [-] answer for test:    {answer}')

    print("\n[*] done")


VERSION = '3.2'
LOGO = (
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

FUNC_NAME = {
    "b64": "base64_encode",
    "base64": "base64_encode",
    "base64encode": "base64_encode",

    "hex": "hex_encode",
    "hexencode": "hex_encode",

    "url": "url_decode",
    "urldecode": "url_decode",
}

if __name__ == '__main__':
    cli()
