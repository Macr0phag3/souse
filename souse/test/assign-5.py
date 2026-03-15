import os
import requests

my_dict = {}
my_dict[os.name] = requests.status_codes.codes.ALL_OK

# b'(dp0\ncbuiltins\ngetattr\np1\ncrequests\nstatus_codes\np2\ncos\nname\np3\ng0\n(g3\ng1\n(g1\n(g2\nVcodes\ntRVALL_OK\ntRu.'
