import pickle
import re

from colorama import Fore

from souse.explain import explain


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def test_explain_final_value_uses_updated_list_and_dict_state():
    list_output = _plain(explain(pickle.dumps([1, 2], protocol=4)))
    dict_output = _plain(explain(pickle.dumps({"a": 1, "b": 2}, protocol=4)))

    assert "final-value: [1, 2]" in list_output
    assert "final-value: {'a': 1, 'b': 2}" in dict_output


def test_explain_singleton_tuple_keeps_trailing_comma():
    for protocol in (0, 1):
        output = _plain(explain(pickle.dumps((1,), protocol=protocol)))
        assert "final-value: (1,)" in output


def test_explain_shows_accumulated_opcode_trace():
    output = _plain(explain(b"crequests\napi\np0\n."))
    assert "opcode: crequests\\napi\\n" in output
    assert "opcode: crequests\\napi\\np0\\n" in output


def test_explain_highlights_new_opcode_bytes_in_yellow():
    output = explain(b"crequests\napi\np0\n.")
    opcode_lines = [line for line in output.splitlines() if "    opcode: " in line]

    assert Fore.YELLOW in opcode_lines[0]
    assert Fore.GREEN in opcode_lines[1]
    assert Fore.YELLOW in opcode_lines[1]


def test_explain_bool_and_build_meanings_are_more_natural():
    bool_output = _plain(explain(b"I01\n."))
    build_output = _plain(explain(b"crequests\napi\np0\ncbuiltins\ngetattr\np1\n(g0\nVget\ntR(N}Va\nI1\nstb."))
    reduce_output = _plain(explain(b"cbuiltins\ngetattr\np0\n(crequests\napi\nVget\ntR."))

    assert "meaning: 压入布尔值 True" in bool_output
    assert "meaning: 给 builtins.getattr(requests.api, 'get') 设置属性 a = 1" in build_output
    assert "meaning: 从 builtins 导入 getattr" in reduce_output
    assert "meaning: 从 requests 导入 api" in reduce_output
    assert "meaning: 调用 builtins.getattr(requests.api, 'get')" in reduce_output


def test_explain_constructor_meanings_are_specific():
    newobj_output = _plain(explain(b"cbuiltins\nlist\np0\n(t\x81p1\n."))
    newobj_ex_output = _plain(explain(b"cbuiltins\ndict\np0\n(t(Va\nI1\nd\x92p1\n."))
    obj_output = _plain(explain(b"cos\nsystem\np0\nVwhoami\np1\n(g0\ng1\no."))
    inst_output = _plain(explain(b"cos\nsystem\np0\nVwhoami\np1\n(g1\nios\nsystem\n."))

    assert "meaning: 调用 builtins.list()" in newobj_output
    assert "meaning: 调用 builtins.dict(a=1)" in newobj_ex_output
    assert "meaning: 调用 os.system('whoami')" in obj_output
    assert "meaning: 调用 os.system('whoami')" in inst_output
