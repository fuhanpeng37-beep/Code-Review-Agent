"""Read-only tools. Target source is parsed, never executed."""
import ast
import json
from pathlib import Path

MAX_BYTES = 64_000
ALLOWED = {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.c', '.cpp', '.h', '.go', '.rs', '.md', '.txt'}


def schema(name, description):
    return {'type': 'function', 'function': {
        'name': name, 'description': description, 'strict': True,
        'parameters': {'type': 'object', 'properties': {'path': {'type': 'string'}},
                       'required': ['path'], 'additionalProperties': False}}}


SCHEMAS = [
    schema('list_files', '列出目录内可审查的源文件和子目录。path 使用相对路径，根目录为 .'),
    schema('read_file', '读取源文件并返回行号。最大 64 KB，UTF-8 编码。'),
    schema('analyze_python', '使用 AST 检查 Python 的可变默认参数、裸 except、eval/exec 和语法错误。'),
]


class Tools:
    def __init__(self, root):
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise ValueError('工作目录不存在')

    def resolve(self, path):
        if not isinstance(path, str) or not path or Path(path).is_absolute():
            raise ValueError('path 必须为非空相对路径')
        lexical = Path(path)
        if any(p.startswith('.') and p not in {'.', '..'} for p in lexical.parts):
            raise ValueError('不允许访问隐藏文件或目录')
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError('路径超出工作目录')
        if any(p.startswith('.') for p in target.relative_to(self.root).parts):
            raise ValueError('不允许访问隐藏文件或目录')
        return target

    def source(self, path):
        target = self.resolve(path)
        if not target.is_file() or target.suffix.lower() not in ALLOWED:
            raise ValueError('文件不存在或扩展名不在允许列表中')
        with target.open('rb') as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('文件超过 64 KB，请拆分后审查')
        return data.decode('utf-8')

    def list_files(self, path):
        folder = self.resolve(path)
        if not folder.is_dir():
            raise ValueError('目标不是目录')
        entries = []
        truncated = False
        for item in folder.iterdir():
            if item.name.startswith('.') or item.is_symlink() or item.name in {'node_modules', '__pycache__', 'venv'}:
                continue
            if item.is_dir() or item.suffix.lower() in ALLOWED:
                entries.append(str(item.relative_to(self.root)) + ('/' if item.is_dir() else ''))
            if len(entries) >= 200:
                truncated = True
                break
        return {'files': sorted(entries), 'truncated': truncated}

    def read_file(self, path):
        source = self.source(path)
        return {'path': path, 'content': '\n'.join(f'{i}: {s}' for i, s in enumerate(source.splitlines(), 1))}

    def analyze_python(self, path):
        if Path(path).suffix != '.py':
            raise ValueError('AST 工具仅支持 .py 文件')
        source = self.source(path)
        findings = []

        def add(node, rule, severity, message, suggestion):
            findings.append({'line': node.lineno, 'rule': rule, 'severity': severity,
                             'message': message, 'suggestion': suggestion})
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return {'path': path, 'findings': [{'line': exc.lineno, 'rule': 'syntax-error',
                    'severity': 'high', 'message': exc.msg, 'suggestion': '先修复语法错误再进行审查。'}]}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for value in node.args.defaults + node.args.kw_defaults:
                    if isinstance(value, (ast.List, ast.Dict, ast.Set)):
                        add(value, 'mutable-default', 'medium', '可变默认参数会在多次调用间共享状态。',
                            '使用 None 作为默认值，在函数内部创建新容器。')
            elif isinstance(node, ast.ExceptHandler) and node.type is None:
                add(node, 'bare-except', 'medium', '裸 except 可能捕获退出和中断信号并掩盖错误。',
                    '捕获明确的异常类型，并记录或重新抛出异常。')
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {'eval', 'exec'}:
                add(node, 'dynamic-execution', 'high', '动态执行表达式或代码，若输入不可信可能造成任意代码执行。',
                    '避免动态执行；数据解析可使用 json.loads 或按场景使用 ast.literal_eval。')
        return {'path': path, 'findings': sorted(findings, key=lambda f: f['line']),
                'note': '规则仅覆盖部分语法模式；未命中不代表代码没有问题。'}

    def call(self, name, arguments):
        try:
            if name not in {'list_files', 'read_file', 'analyze_python'}:
                raise ValueError('未知工具')
            args = json.loads(arguments)
            if not isinstance(args, dict) or set(args) != {'path'}:
                raise ValueError('参数必须仅包含 path')
            return {'ok': True, 'result': getattr(self, name)(args['path'])}
        except (ValueError, OSError, UnicodeError, TypeError, RecursionError) as exc:
            return {'ok': False, 'error': str(exc)}
