from requests import get

get.a = 1
get.b = "2"
get.c = (1, "2")

get.d = (get.a, get.b) # NOT supported
# b'crequests\nget\np0\ng0\n(N}Va\nI1\nstbg0\n(N}Vb\nV2\nstbg0\n(N}Vc\n(I1\nV2\ntstbg0\n(N}Vd\n(cbuiltins\ngetattr\np1\n(g0\nVa\ntRg1\n(g0\nVb\ntRtstb.'
