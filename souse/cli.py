import argparse
import os
import re
import shutil

from colorama import Fore, Style, init as Init  # type: ignore

from .api import API
from .tools import FUNC_NAME, transfer_funcs, put_color


VERSION = '5.2'
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


def _parse_firewall_rules(payload: str) -> list[str]:
    return [item.strip() for item in payload.split(",") if item.strip()]


def cli() -> None:
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
        help="run test with cases/*.py (not startswith `N-`)"
    )
    parser.add_argument(
        "-p", "--bypass", default=False,
        help="try bypass limitation"
    )
    parser.add_argument(
        "-t", "--transfer", default=None,
        help=f"transfer result with: { {i for i in FUNC_NAME.values()} }"
    )
    parser.add_argument(
        "--explain", action="store_true",
        help="show opcode summary and explanation view"
    )

    args = parser.parse_args()

    need_check = args.check
    need_optimize = args.no_optimize
    run_test = args.run_test
    transfer = args.transfer
    explain = args.explain
    transfer_func = transfer_funcs(transfer)

    if run_test:
        # 代码质量测试模式下
        # 不优化 opcode、不执行 opcode、不 bypass
        need_optimize = False
        need_check = False
        directory = os.path.join(
            os.path.dirname(__file__), "cases"
        )
        filenames = sorted([
            os.path.join(directory, i) for i in list(os.walk(directory))[0][2]
            if not i.startswith("N-")
        ])
    else:
        filenames = [args.filename]

    print(f'[*] need check:        {put_color(need_check, ["gray", "green"][int(need_check)])}')
    print(f'[*] need optimize:     {put_color(need_optimize, ["gray", "green"][int(need_optimize)])}')

    firewall_rules = []
    bypass = False

    if args.bypass:
        try:
            firewall_rules = _parse_firewall_rules(args.bypass)
        except Exception as e:
            try:
                firewall_rules = _parse_firewall_rules(open(args.bypass, encoding='utf-8').read())
            except Exception as e:
                print("\n[!]", put_color(f"{args.bypass} has invalid bypass rules: {e}\n", 'yellow'))
            else:
                if not firewall_rules:
                    print("\n[!]", put_color(f"{args.bypass} has no rules\n", 'yellow'))
                else:
                    bypass = True
        else:
            if firewall_rules:
                bypass = True

    print(f'[*] try bypass:        {put_color(args.bypass, ["gray", "cyan"][int(bypass)])}')
    print(f'[*] transfer function: {put_color(transfer, ["blue", "gray"][bool(bypass)])}\n')

    for filename in filenames:
        tip = lambda c: f'[+] input: {put_color(filename, c)}'

        source_code = open(filename, encoding='utf-8').read()
        if run_test:
            firewall_rules = []
            for line in source_code.splitlines():
                stripped = line.strip()
                if stripped.startswith("# firewall:"):
                    payload = stripped[len("# firewall:"):].strip()
                    try:
                        firewall_rules = _parse_firewall_rules(payload)
                    except Exception as e:
                        raise RuntimeError(f"invalid firewall rules in test file: {e}")

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
                    if not explain:
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

        if visitor.has_transformation and visitor.converted_code:
            print(f'  [-] converted code: ')
            for line in visitor.converted_code:
                print(f'      {put_color(line, "gray")}')

        if explain:
            explain_data = visitor.optimize() if need_optimize else visitor.result
            print(visitor.explain(explain_data))

        if run_test:
            loc = [
                (i, j)
                for i, j in zip(enumerate(str(visitor.result)), enumerate(answer))
                if i[1] != j[1]
            ][0][0][0]
            answer = (
                put_color(answer[:loc], "green") + put_color(answer[loc:-1], "yellow") + put_color(answer[-1], "green") # type: ignore
            )
            print(f'  [-] answer for test:    {answer}')

    if run_test:
        tests_dir = os.path.join(os.getcwd(), "tests")
        if not os.path.isdir(tests_dir):
            print("\n[*] pytest skipped (no tests/)")
            return

        try:
            import pytest, pytest_cov  # noqa: F401
        except Exception:
            print("\n[!] pytest and coverage is not installed; skip running pytest -q")
        else:
            result = os.popen("pytest --cov").read()
            passed = re.findall("(\\d+) passed in", result)
            failed = re.findall("(\\d+) failed", result)
            fmsg = "" if not failed else f", failed: {put_color(failed[0], 'yellow')}"
            cov = re.findall("TOTAL\\s+\\d+\\s+\\d+\\s+(\\d+%)", result)
            print(f"\n[*] pytest success: {put_color(passed[0], 'green')}{fmsg}")
            print(f"[*] test coverage: {put_color(cov[0], 'green')}")
            
            os.remove(".coverage")
            shutil.rmtree(".pytest_cache", ignore_errors=True)

    print("\n[*] done")
