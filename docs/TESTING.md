# 测试记录

验证日期：2026-10-11。环境：macOS，Python 3.12.14。

## 自动化测试

在项目根目录执行：

```bash
python3 -m unittest discover -s tests -v
```

结果：23 项测试通过，0 失败。完整输出见 [test_output.txt](test_output.txt)。

| 测试层 | 数量 | 覆盖内容 |
| --- | --- | --- |
| 工具 | 8 | AST 规则与行号、语法错误、关键字默认值、路径与隐藏文件、符号链接、错误参数、大文件与编码、目录和修复样本 |
| Agent | 7 | 工具闭环、上下文追问、失败回滚、循环上限、工具错误反馈、完整轮次裁剪、异常消息、离线报告（部分合并于同一测试） |
| HTTP 客户端 | 5 | 请求结构、429 重试、401 不重试和不泄露密钥、网络重试耗尽、错误 JSON、配置校验（部分合并于同一测试） |
| CLI | 3 | 离线导出和 trace、缺少密钥、无效工作目录 |

## 端到端离线流程

```bash
python3 -m code_review_agent --demo --trace --output docs/demo_report.md
```

退出码为 0。工具实际读取 `examples/buggy.py` 并运行 AST 检查，定位可变默认参数（第 4 行）、裸 except（第 12 行）和 eval 调用（第 17 行）。结果见 [demo_report.md](demo_report.md)，调用轨迹见 [demo_trace.txt](demo_trace.txt)。

## 验证边界

自动化测试通过模型替身验证 Agent 协议，通过模拟 HTTP 返回验证传输处理。它们未请求真实模型服务。离线演示同样未调用 LLM。

在线模型的可用性、工具选择质量和中文报告质量仍需配置用户自己的 API Key 后验收。建议按 README 的在线命令运行含问题样本，再审查修复样本并提出一轮追问；检查工具日志、报告行号和上下文连贯性。尚未执行该项，不将模拟测试结果表述为真实服务联调成功。
