# # souse
A tool for converting Python source code to opcode(pickle)

## ## help

<img src="/pics/help.png" width="600">


## ## usage

`./test/` has some example codes for souse.py. The filename starts with `N` is NOT supported yet.

### ### case 1

source code:

<img src="/pics/eg-1.png" width="300">

opcode:

<img src="/pics/eg-1-s.png" width="600">

### ### case 2

source code:

<img src="/pics/eg-2.png" width="300">

opcode:

<img src="/pics/eg-2-s.png" width="600">

### ### case 3

transfer opcode:

<img src="/pics/eg-3.png" width="600">

supported:
- [x] base64_encode
- [x] hex_encode
- [x] url_encode

### ### test code

<img src="/pics/test.png" width="400">

## ## TODO
- [x] support for nested expressions
- [x] basic bypass support

## ## Others
<img src="https://clean-1252075454.cos.ap-nanjing.myqcloud.com/20200528120800990.png" width="500">

[![Stargazers over time](https://starchart.cc/Macr0phag3/souse.svg)](https://starchart.cc/Macr0phag3/souse)
