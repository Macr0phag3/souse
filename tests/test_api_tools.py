import base64
import pickle
import pickletools
from pathlib import Path

import pytest

from souse.api import API
from souse.tools import transfer_funcs


def test_transfer_funcs_aliases_and_identity():
    payload = b"abc"
    assert transfer_funcs(None)(payload) == payload
    assert transfer_funcs("")(payload) == payload
    assert transfer_funcs("b64")(payload) == base64.b64encode(payload)
    assert transfer_funcs("base64_encode")(payload) == base64.b64encode(payload)
    assert transfer_funcs("hex")(payload) == b"616263"
    assert transfer_funcs("url")("a b") == "a+b"


def test_transfer_funcs_invalid_name():
    with pytest.raises(RuntimeError):
        transfer_funcs("no_such_transfer")


def test_api_transfer_list_and_callable():
    source = "a = 1"
    raw = API(source, optimized=False, transfer="").generate()

    via_list = API(
        source,
        optimized=False,
        transfer=[bytes.decode, str.encode, base64.b64encode],
    ).generate()
    assert via_list == base64.b64encode(raw)

    via_callable = API(
        source,
        optimized=False,
        transfer=base64.b64encode,
    ).generate()
    assert via_callable == base64.b64encode(raw)

    via_string = API(
        source,
        optimized=False,
        transfer="b64",
    ).generate()
    assert via_string == base64.b64encode(raw)


def test_optimize_preserves_value():
    source = "a = 1\na"
    visitor = API(source, optimized=False, transfer="")._generate()
    raw = visitor.result
    optimized = visitor.optimize()

    assert pickle.loads(raw) == 1
    assert pickle.loads(optimized) == 1
    assert len(optimized) <= len(raw)


def test_float_constant_generation():
    source = "a = 1.5"
    result = API(source, optimized=False, transfer="").generate()
    assert result == b"F1.5\np0\n."


def test_large_int_can_bypass_to_long1():
    source = f"a = {2 ** 100}"
    result = API(source, firewall_rules=["I"], optimized=False, transfer="").generate()

    assert result.startswith(b"\x8a")
    assert pickle.loads(result) == 2 ** 100


def test_huge_int_can_bypass_to_long4():
    source = f"a = {1 << 3000}"
    result = API(source, firewall_rules=["I", "\\x8a"], optimized=False, transfer="").generate()

    assert result.startswith(b"\x8b")
    assert pickle.loads(result) == 1 << 3000


def test_small_tuple_can_bypass_to_tuple1_tuple2_tuple3():
    result1 = API("a = (1,)", firewall_rules=["t"], optimized=False, transfer="").generate()
    result2 = API("a = (1, 2)", firewall_rules=["t"], optimized=False, transfer="").generate()
    result3 = API("a = (1, 2, 3)", firewall_rules=["t"], optimized=False, transfer="").generate()

    assert b"\x85" in result1
    assert b"\x86" in result2
    assert b"\x87" in result3
    assert pickle.loads(result1) == (1,)
    assert pickle.loads(result2) == (1, 2)
    assert pickle.loads(result3) == (1, 2, 3)


def test_empty_containers_can_bypass_to_empty_opcodes():
    list_result = API("a = []", firewall_rules=["l"], optimized=False, transfer="").generate()
    tuple_result = API("a = ()", firewall_rules=["t"], optimized=False, transfer="").generate()
    dict_result = API("a = {}", firewall_rules=["d"], optimized=False, transfer="").generate()

    assert list_result.startswith(b"]")
    assert tuple_result.startswith(b")")
    assert dict_result.startswith(b"}")
    assert pickle.loads(list_result) == []
    assert pickle.loads(tuple_result) == ()
    assert pickle.loads(dict_result) == {}


def test_list_and_dict_can_bypass_to_appends_and_setitems():
    list_result = API("a = [1, 2]", firewall_rules=["l"], optimized=False, transfer="").generate()
    dict_result = API("a = {'x': 1, 'y': 2}", firewall_rules=["d"], optimized=False, transfer="").generate()

    assert list_result.startswith(b"](")
    assert b"e" in list_result
    assert dict_result.startswith(b"}(")
    assert b"u" in dict_result
    assert pickle.loads(list_result) == [1, 2]
    assert pickle.loads(dict_result) == {"x": 1, "y": 2}


def test_set_can_bypass_to_additems():
    result = API("a = {1, 2}", firewall_rules=["R"], optimized=False, transfer="").generate()

    assert result.startswith(b"\x8f(")
    assert b"\x90" in result
    assert pickle.loads(result) == {1, 2}


def test_memo_can_bypass_to_memoize():
    result = API("a = 1\na", firewall_rules=["p"], optimized=False, transfer="").generate()

    assert b"\x94" in result
    assert pickle.loads(result) == 1


def test_stack_global_can_bypass_global_for_attribute():
    result = API(
        "import os\ncurrent = os.getcwd\ncurrent\n",
        firewall_rules=["c"],
        optimized=False,
        transfer="",
    ).generate()

    assert b"\x93" in result
    assert pickle.loads(result) == __import__("os").getcwd


def test_mass_assignment_unsupported():
    source = "a, b = 1, 2"
    with pytest.raises(RuntimeError):
        API(source, optimized=False, transfer="").generate()


def test_optimize_handles_combo_7_case_without_invalid_memo_order():
    source = Path("souse/cases/combo-7.py").read_text()
    visitor = API(source, optimized=False, transfer="")._generate()

    optimized = visitor.optimize()

    assert optimized
    assert list(pickletools.genops(visitor.result))
    assert list(pickletools.genops(optimized))
