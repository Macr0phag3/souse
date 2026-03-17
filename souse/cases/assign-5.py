import os
import requests

my_dict = {}
my_dict[os.name] = requests.status_codes.codes.ALL_OK

# b'(dp0\ncrequests\nstatus_codes\np1\ncos\nname\np3\ng0\n(g3\ng2\n(cbuiltins\ngetattr\np2\n(g1\nVcodes\ntRVALL_OK\ntRu.'
