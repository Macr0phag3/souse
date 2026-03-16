# souse
一个将 Python 源码全自动化转换为 Opcode (pickle) 的工具，源码即 Payload :)

[English Version](./README.md)

## 1. 帮助信息

<img src="https://raw.githubusercontent.com/Macr0phag3/souse/master/pics/help.png" width="600">

## 2. 核心特性

- **🚀 智能重构**: 自动将原本无法直接序列化的 Python 源码重构为完全兼容的 Pickle 指令流（例如：自动将下标赋值 `a[k]=v` 转换为 `__setitem__` 调用）。
- **✨ 自动化内置支持**: 自动识别并导出 `open`、`eval`、`getattr` 等 Python 内置函数，无需手动导入，开箱即用。
- **🛡️ 灵活防火墙绕过**: 针对 `R`、`o`、`i`、`u`、`b` 等核心指令提供多种自动化绕过方案，支持自定义指令禁用规则。
- **⚡ 极致 Payload 优化**: 内置 `pickletools` 优化逻辑，自动精简指令流，确保 Payload 体积最小且隐蔽性最高。
- **📦 多功能转换包装**: 支持 Base64、Hex、URL 等多种编码输出，并允许自定义转换函数序列。
- **📝 精准调试与上下文**: 提供带源码上下文的错误报告，精准定位不支持的语法结构，极大提升 Payload 开发效率。
- **💡 完善的 API 支持**: 除命令行外，支持通过 Python API 深度集成到自动化任务中。

## 3. 使用方法
### 3.1 命令行 (CLI)
`./test/` 目录下有一些演示代码。

示例见原版 [README](./README.md#21-cli)。

#### 3.1.0 提示
你可以通过在源码最后一行写变量名，来控制反序列化的最终返回值。

示例：
```py
a = "whoami"
a
```

### 3.2 编程接口 (API)
示例：

```py
import souse
import pickle

exp = "from os import system\nsystem('whoami')"

# 使用 API 进行转换，并应用防火墙绕过规则
firewall_rules = {"R": "*", "V": "*"}
result = souse.API(exp, optimized=True, transfer=pickle.loads, firewall_rules=firewall_rules).generate()

# 输出：
# [*] choice o to bypass rule: {'R': '*'}
# [*] choice S to bypass rule: {'V': '*'}
# macr0phag3
```

## 4. 开发计划 (TODO)
- [x] 支持嵌套表达式 (Nested expressions)
- [x] 指令级防火墙绕过 (Opcode bypass)
- [x] 智能导入转换 (Lazy Import)
- [x] 智能属性/下标赋值转换
- [x] 转换后的代码回显示支持
- [x] 基于值的防火墙绕过 (Value bypass)
- [x] Python API 支持
- [x] 源码级报错上下文提示
- [x] 自动化内置函数识别

---
## 其他
<img src="https://clean-1252075454.cos.ap-nanjing.myqcloud.com/20200528120800990.png" width="500">

[![Stargazers over time](https://starchart.cc/Macr0phag3/souse.svg)](https://starchart.cc/Macr0phag3/souse)
