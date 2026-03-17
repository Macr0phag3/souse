a = list(set((1, 2)))
b = tuple(list(set((3, 4))))
# firewall: {"R": "*"}
# b'(cbuiltins\nlist\np0\n(cbuiltins\nset\np1\n(I1\nI2\ntoop2\n(cbuiltins\ntuple\np3\n(g0\n(g1\n(I3\nI4\ntooop4\n.'
