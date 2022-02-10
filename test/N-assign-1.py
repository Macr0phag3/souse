from requests import get

get.a = 1
get.b = "2"
get.c = (1, "2")

get.d = (get.a, get.b) # NOT supported
