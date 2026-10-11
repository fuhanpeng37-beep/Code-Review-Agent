"""Deterministic offline backend, explicitly not a language model."""
import json


class DemoClient:
    def complete(self, messages, tools):
        last_user = max(i for i, m in enumerate(messages) if m['role'] == 'user')
        current = messages[last_user + 1:]
        results = [json.loads(m['content']) for m in current if m['role'] == 'tool']
        if not results:
            return {'content': None, 'tool_calls': [
                {'id': 'demo_read', 'type': 'function', 'function': {
                    'name': 'read_file', 'arguments': '{"path":"examples/buggy.py"}'}},
                {'id': 'demo_ast', 'type': 'function', 'function': {
                    'name': 'analyze_python', 'arguments': '{"path":"examples/buggy.py"}'}}]}
        lines = ['# 离线演示审查报告', '',
                 '此报告由确定性演示后端根据真实工具输出生成，未调用 LLM。', '',
                 '## 审查范围', 'examples/buggy.py，文件读取与 AST 静态分析。', '', '## 问题']
        for result in results:
            if not result['ok']:
                lines.append('- 工具错误：' + result['error'])
            else:
                for f in sorted(result['result'].get('findings', []),
                                key=lambda item: ({'high': 0, 'medium': 1, 'low': 2}[item['severity']], item['line'])):
                    lines.append(f"- **{f['severity']}** `examples/buggy.py:{f['line']}` [{f['rule']}] "
                                 f"{f['message']} 建议：{f['suggestion']}")
        lines += ['', '## 测试建议', '重复调用 add_item，验证调用之间是否共享列表；检查异常处理是否保留错误信息。',
                  '', '## 局限', '离线演示仅运行固定流程和静态规则，不能理解任意问题或提供模型推理。',
                  '在线模式配置 API Key 和支持工具调用的模型后，可审查其他文件并进行上下文追问。']
        return {'content': '\n'.join(lines)}
