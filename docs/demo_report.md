# 离线演示审查报告

此报告由确定性演示后端根据真实工具输出生成，未调用 LLM。

## 审查范围
examples/buggy.py，文件读取与 AST 静态分析。

## 问题
- **high** `examples/buggy.py:17` [dynamic-execution] 动态执行表达式或代码，若输入不可信可能造成任意代码执行。 建议：避免动态执行；数据解析可使用 json.loads 或按场景使用 ast.literal_eval。
- **medium** `examples/buggy.py:4` [mutable-default] 可变默认参数会在多次调用间共享状态。 建议：使用 None 作为默认值，在函数内部创建新容器。
- **medium** `examples/buggy.py:12` [bare-except] 裸 except 可能捕获退出和中断信号并掩盖错误。 建议：捕获明确的异常类型，并记录或重新抛出异常。

## 测试建议
重复调用 add_item，验证调用之间是否共享列表；检查异常处理是否保留错误信息。

## 局限
离线演示仅运行固定流程和静态规则，不能理解任意问题或提供模型推理。
在线模式配置 API Key 和支持工具调用的模型后，可审查其他文件并进行上下文追问。
