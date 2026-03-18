import os
import requests

my_dict = {}
my_dict[os.name] = requests.status_codes.codes.ALL_OK

# b'(dp0\ncos\nname\np1\ncbuiltins\ngetattr\np2\ncrequests\nstatus_codes\np3\ng0\n(g1\ng2\n(g2\n(g3\nVcodes\ntRVALL_OK\ntRu.'
