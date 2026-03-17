from requests import get, post

get.a = 1
post.b = get.a
# b'crequests\nget\np0\ncrequests\npost\np1\ng0\n(N}Va\nI1\nstbg1\n(N}Vb\ncbuiltins\ngetattr\np2\n(g0\nVa\ntRstb.'
