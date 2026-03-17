"""Compatibility wrapper for legacy imports."""

if __package__ is None or __package__ == "":
    # Allow running as a script: `python souse/souse.py --run-test`
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    from souse.api import API
    from souse.cli import LOGO, VERSION, cli
    from souse.opcodes import Opcodes
    from souse.tools import FUNC_NAME, transfer_funcs, put_color
    from souse.visitor import Visitor
else:
    from .api import API
    from .cli import LOGO, VERSION, cli
    from .opcodes import Opcodes
    from .tools import FUNC_NAME, transfer_funcs, put_color
    from .visitor import Visitor

__all__ = [
    "API",
    "cli",
    "Visitor",
    "Opcodes",
    "transfer_funcs",
    "put_color",
    "VERSION",
    "LOGO",
    "FUNC_NAME",
]

if __name__ == '__main__':
    cli()
