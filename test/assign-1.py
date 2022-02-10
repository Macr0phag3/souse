from requests import get
from builtins import set, tuple, list, frozenset


get.a1 = 1
get.a2 = "2"
get.b1 = set()
get.b2 = frozenset()
get.b3 = ()
get.b4 = tuple()
get.b5 = []
get.b6 = list()

get.c1 = {}
get.c2 = {1, "2", get}
get.c3 = {1: 3, None: 2, "1": "2", get: 3}
get.c4 = (1, "2", get)
get.c5 = (None, True, False)

# b'crequests\nget\np0\ncbuiltins\nset\np1\ncbuiltins\ntuple\np2\ncbuiltins\nlist\np3\ncbuiltins\nfrozenset\np4\ng0\n(N}Va1\nI1\nstbg0\n(N}Va2\nV2\nstbg0\n(N}Vb1\ng1\n(tRstbg0\n(N}Vb2\ng4\n(tRstbg0\n(N}Vb3\n(tstbg0\n(N}Vb4\ng2\n(tRstbg0\n(N}Vb5\n(lstbg0\n(N}Vb6\ng3\n(tRstbg0\n(N}Vc1\n(dstbg0\n(N}Vc2\n\x8f(I1\nV2\ng0\n\x90stbg0\n(N}Vc3\n(I1\nI3\nNI2\nV1\nV2\ng0\nI3\ndstbg0\n(N}Vc4\n(I1\nV2\ng0\ntstbg0\n(N}Vc5\n(NI01\nI00\ntstb.'

