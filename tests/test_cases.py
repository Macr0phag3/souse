import pytest

from souse.api import API


def _generate(source: str, firewall_rules=None):
    return API(
        source,
        firewall_rules=firewall_rules or {},
        optimized=False,
        transfer="",
    ).generate()


def test_assign_attr_imported_function():
    source = (
        """from requests import get\n\n"""
        """get.a = 1"""
    )
    expected = b"crequests\nget\np0\ng0\n(N}Va\nI1\nstb."
    assert _generate(source) == expected


def test_assign_attr_module_member():
    source = (
        """import requests\n\n"""
        """requests.get = 1"""
    )
    expected = b"crequests\nget\np0\nI1\np1\n."
    assert _generate(source) == expected


def test_assign_nested_attr_uses_getattr():
    source = (
        """import requests\n\n"""
        """requests.api.get.a = 1"""
    )
    expected = b"crequests\napi\np0\ncbuiltins\ngetattr\np1\n(g0\nVget\ntR(N}Va\nI1\nstb."
    assert _generate(source) == expected


def test_subscript_assign_setitem():
    source = (
        """from builtins import globals\n\n"""
        """globals()["PWD"] = "tr0y" """
    )
    expected = b"cbuiltins\nglobals\np0\ng0\n(tR(VPWD\nVtr0y\nu."
    assert _generate(source) == expected


def test_subscript_assign_firewall_u_bypass():
    source = (
        """a = {}\n"""
        """a["x"] = 1"""
    )
    expected = b"(dp0\ncbuiltins\ngetattr\np1\n(g0\nV__setitem__\ntR(Vx\nI1\ntR."
    assert _generate(source, {"u": "*"}) == expected


def test_bool_firewall_uses_bintrue_false():
    source = (
        """a = True\n"""
        """b = False"""
    )
    expected = b"\x88p0\n\x89p1\n."
    assert _generate(source, {"I01": "*", "I00": "*"}) == expected


def test_string_firewall_uses_binstring():
    source = """a = "abc" """
    expected = b"S'abc'\np0\n."
    assert _generate(source, {"V": "*"}) == expected


def test_int_firewall_uses_binint():
    source = """a = 1"""
    expected = b"J\x01\x00\x00\x00p0\n."
    assert _generate(source, {"I": "*"}) == expected


def test_call_firewall_falls_back_to_inst():
    source = (
        """from os import system\n\n"""
        """a = "whoami"\n"""
        """system(a)"""
    )
    expected = b"cos\nsystem\np0\nVwhoami\np1\n(g1\nios\nsystem\n."
    assert _generate(source, {"R": "*", "o": "*"}) == expected


def test_call_newobj_without_keywords():
    source = (
        """a = list()"""
    )
    expected = b"cbuiltins\nlist\np0\n(t\x81p1\n."
    assert _generate(source, {"R": "*", "o": "*", "i": "*"}) == expected


def test_call_newobj_ex_with_keywords():
    source = (
        """a = dict(a=1)"""
    )
    expected = b"cbuiltins\ndict\np0\n(t(Va\nI1\nd\x92p1\n."
    assert _generate(source, {"R": "*", "o": "*", "i": "*", "\\x81": "*"}) == expected


def test_subscript_getitem_transforms_to_getattr():
    source = (
        """import os\n"""
        """a = os.environ["PATH"]"""
    )
    expected = b"cos\nenviron\np0\ncbuiltins\ngetattr\np1\n(g0\nV__getitem__\ntR(VPATH\ntRp2\n."
    assert _generate(source) == expected


def test_unary_negative_int():
    source = (
        """a = -3"""
    )
    expected = b"I-3\np0\n."
    assert _generate(source) == expected


def test_unsupported_mass_assignment():
    source = "a, b = 1, 2"
    with pytest.raises(RuntimeError):
        _generate(source)
