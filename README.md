# Code Review Agent · Homework 1

一个通过命令行交互的代码审查助手。在线模式由大模型选择工具、读取代码、检查 Python AST，再生成带行号的中文审查报告，并支持继续追问。项目使用 Python 标准库，便于阅读 Agent 的核心实现。

## 作业要求对应

| 作业要求 | 本项目实现 |
| --- | --- |
| 选择一种代码助手方向 | 代码审查 Agent |
| 输入、推理、工具调用、输出 | `agent.py` 中的有界工具调用循环 |
| 至少一种工具 | `list_files`、`read_file`、`analyze_python` |
| 命令行或 Web 交互 | 单次命令和交互式命令行 |
| LLM 调用与 Prompt 设计 | Chat Completions 兼容接口和中文系统提示词 |
| 上下文记忆 | 保存最近 4 个完整成功对话轮次，支持 `/reset` |
| 错误处理与重试 | 工具错误反馈、网络重试、循环上限、失败轮次回滚 |
| 源码与文档 | 源码、测试、README、Design.md 和示例报告 |

## 1. 运行环境

需要 Python 3.10 或更高版本，无第三方依赖。以下所有命令都在本 README 所在的 `homework1` 目录运行。

```bash
cd homework1
python3 --version
```

Windows 可将命令中的 `python3` 替换为 `py -3` 或对应的 Python 命令。

## 2. 无需密钥的离线演示

```bash
python3 -m code_review_agent --demo --trace
python3 -m code_review_agent --demo --output reports/demo.md
```

演示会通过真实工具读取 `examples/buggy.py`，使用 AST 检出可变默认参数、裸 `except` 和 `eval` 调用，再生成报告。`--trace` 显示实际工具调用记录。

**演示后端为固定流程，不调用大模型，不理解任意自然语言问题，也不展示模型推理能力。** `--demo` 始终使用 `examples/buggy.py`；应在本项目根目录运行。预先生成的结果见 [docs/demo_report.md](docs/demo_report.md)。

## 3. 启用真实模型

需要一个支持 Chat Completions 和 function tools 的模型服务及其 API Key。程序读取以下环境变量：

| 变量 | 含义 |
| --- | --- |
| `LLM_API_KEY` | 服务商 API Key，必填 |
| `LLM_MODEL` | 你账户可访问、支持工具调用的模型 ID，必填 |
| `LLM_BASE_URL` | API 前缀，默认 `https://api.openai.com/v1` |

macOS / Linux：

```bash
export LLM_API_KEY='替换为你的密钥'
export LLM_MODEL='替换为支持工具调用的模型ID'
export LLM_BASE_URL='https://api.openai.com/v1'
python3 -m code_review_agent '请审查 examples/buggy.py，按严重程度解释问题并给出修复建议。' --trace
```

Windows PowerShell：

```powershell
$env:LLM_API_KEY = '替换为你的密钥'
$env:LLM_MODEL = '替换为支持工具调用的模型ID'
$env:LLM_BASE_URL = 'https://api.openai.com/v1'
py -3 -m code_review_agent '请审查 examples/buggy.py' --trace
```

`.env.example` 仅是配置样例，程序不会自动加载 `.env`。不要将真实密钥写入源码、报告或提交包。在线模式会将问题、选中的源文件内容和工具结果发送给配置的模型服务。

兼容服务商可以更换 `LLM_BASE_URL` 和模型 ID。地址应为 API 前缀，**不要**再附加 `/chat/completions`。远程服务需要 HTTPS，本机测试支持 localhost 的 HTTP。兼容服务商的工具 schema 支持程度可能不同，需要实际联调。

## 4. 多轮交互和报告导出

```bash
python3 -m code_review_agent --trace
```

输入示例：

```text
你 > 请审查 examples/buggy.py，重点检查实际影响。
你 > 第一个问题在连续调用两次时会怎样？给出最小复现代码。
你 > 请比较 examples/fixed.py 与原文件的区别。
你 > /reset
你 > /exit
```

程序保存最近 4 个成功轮次的完整消息和工具结果。记忆仅存在于当前进程，退出后清除。失败轮次不会破坏已保存的会话。

审查其他项目时，路径相对于 `--root` 指定的目录：

```bash
python3 -m code_review_agent --root /absolute/path/to/project '请先列出根目录文件，然后审查 main.py。' --output reports/review.md
```

`--output` 保存 UTF-8 Markdown，并覆盖同名目标文件。交互模式中每次成功回答都会更新同一输出文件，因此建议需要保存独立报告时使用单次命令。程序只读取待审查项目，不会自动修改源码或执行源码。

## 5. 项目结构

```text
homework1/
  code_review_agent/
    __main__.py       命令行参数和交互入口
    agent.py          系统提示词、工具循环和会话记忆
    llm.py            HTTP 模型调用与重试
    tools.py          文件工具和 AST 静态分析
    demo.py           明确标记的离线演示后端
  examples/
    buggy.py          含问题的示例代码
    fixed.py          对应修复示例
  tests/test_agent.py 自动化测试
  docs/demo_report.md 实际生成的离线结果
  docs/TESTING.md     测试方法和验证边界
  README.md
  Design.md
  .env.example
  requirements.txt
```

## 6. 测试

```bash
python3 -m unittest discover -s tests -v
```

测试使用模拟模型响应和模拟 HTTP 传输，不需要 API Key、不产生模型费用。覆盖真实工具执行、路径越界和符号链接、错误输入、语法错误、对话上下文、工具调用结果回传、网络重试及失败退出。详见 [测试记录](docs/TESTING.md)。

## 7. 常见问题

- **缺少配置**：设置 `LLM_API_KEY` 和 `LLM_MODEL`，或使用 `--demo`。
- **HTTP 401/403**：检查密钥和模型访问权限，程序不会自动重复身份验证错误。
- **HTTP 429/5xx 或网络超时**：程序对指定的暂时性错误最多重试 2 次，仍失败则返回错误。
- **工具参数错误**：错误会作为工具结果交给模型，以便重新选择工具或修正参数。
- **超出工作目录/文件过大**：工具只允许指定根目录内的非隐藏源文件，每个文件最多 64,000 字节。请调整根目录或拆分文件。
- **循环达到上限**：缩小审查范围，或使用 `--max-steps 12` 调整最大模型请求轮数。
- **没有发现问题**：仅表示当前规则和本次审查没有发现问题，不代表程序一定正确。

## 8. 提交说明

提交源码压缩包即可，本项目未制作演示视频。按课程要求，将压缩包改名为“学号姓名.zip”，上传到指定的 `001Homework1` 位置。课件同时提到 GitHub/Gitee 源码仓库，可将此目录作为仓库内容上传；本交付未代为创建远程仓库或提交课程平台。若课程只接受 RAR，请用归档软件转为 RAR，不要只更改扩展名。

## 技术参考

接口结构参考 [OpenAI Function calling](https://developers.openai.com/api/docs/guides/function-calling) 和 [Create chat completion](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)。实现使用 assistant 的 `tool_calls` 和带 `tool_call_id` 的 tool 消息完成往返。项目未依赖 Agent 框架，以便直接展示调度逻辑。
