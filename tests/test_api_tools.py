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
