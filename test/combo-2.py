from builtins import getattr, dict, globals

get = getattr(dict, 'get')
g = globals()
__builtins__ = get(g, '__builtins__')
f = getattr(__builtins__, 'getattr')(__builtins__, 'getattr')(__builtins__, 'getattr')(__builtins__, 'getattr')(__builtins__, 'setattr')

# b'cbuiltins\ngetattr\np0\ncbuiltins\ndict\np1\ncbuiltins\nglobals\np2\ng0\n(g1\nVget\ntRp3\ng2\n(tRp4\ng3\n(g4\nV__builtins__\ntRp5\ng0\n(g5\nVgetattr\ntR(g5\nVgetattr\ntR(g5\nVgetattr\ntR(g5\nVgetattr\ntR(g5\nVsetattr\ntRp6\n.'
