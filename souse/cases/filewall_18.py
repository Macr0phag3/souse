from os import getcwd

registry = {"cwd": getcwd}
current = registry["cwd"]
current()

# firewall: c
# b'Vos\nVgetcwd\n\x93p0\n(Vcwd\ng0\ndp1\nVbuiltins\nVgetattr\n\x93p2\ng2\n(g1\nV__getitem__\ntR(Vcwd\ntRp3\ng3\n(tR.'
