# CTF Write-up: 2025-1

## 漏洞分析
程序在 `/books/check` 接口使用 `pickle.loads`，虽有 `waf` 但仅检查函数名。限制条件为反序列化对象必须是 `Book` 实例。

## 利用思路

在不破坏题目环境与逻辑的前提下，假设环境无法出网，利用原本的功能进行回显是最好的选择。

所以思路就很简单了，通过 `souse` 生成 Opcode，在反序列化过程中改写全局对象：
1. 从 `__main__` 导入全局 `bookshop`。
2. 篡改 `bookshop.books[0]` 的 `uuid` 为固定值。
3. 篡改其 `name` 为命令执行结果（通过 `os.popen`）。
4. 即使最终 `pickle.loads` 返回的对象不合法，内存中的数据已被污染。
