import functools
from typing import Any, Callable, Optional

from colorama import Fore, Style  # type: ignore


def put_color(string: Any, color: str, bold: bool = True) -> str:
    if color == 'gray':
        COLOR = Fore.LIGHTBLACK_EX
    else:
        COLOR = getattr(Fore, color.upper(), "WHITE")

    style = Style.BRIGHT if bold and color != 'gray' else ""
    return f'{style}{COLOR}{str(string)}{Style.RESET_ALL}'


def transfer_funcs(func_name: Optional[str]) -> Callable:
    if not func_name:
        return lambda x: x

    import base64
    import codecs
    import urllib.parse

    func = {
        'base64_encode': base64.b64encode,
        'hex_encode': functools.partial(codecs.encode, encoding="hex"),
        'url_encode': urllib.parse.quote_plus,
    }.get(FUNC_NAME.get(func_name, func_name))

    if func is None:
        raise RuntimeError(put_color(
            f"no such transfer function: {put_color(func_name, 'blue')}",
            "yellow"
        ))

    return func


FUNC_NAME = {
    "b64": "base64_encode",
    "base64": "base64_encode",
    "base64encode": "base64_encode",

    "hex": "hex_encode",
    "hexencode": "hex_encode",

    "url": "url_encode",
    "urlencode": "url_encode",
}
