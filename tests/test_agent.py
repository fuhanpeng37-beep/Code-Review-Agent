import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from code_review_agent.agent import Agent
from code_review_agent.demo import DemoClient
from code_review_agent.llm import Client, LLMError
from code_review_agent.tools import Tools, MAX_BYTES

ROOT = Path(__file__).resolve().parents[1]


def call(name='read_file', arguments='{"path":"examples/buggy.py"}', cid='c1'):
    return {'content': None, 'tool_calls': [{'id': cid, 'type': 'function',
            'function': {'name': name, 'arguments': arguments}}]}


class ScriptClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def complete(self, messages, tools):
        self.requests.append(copy.deepcopy(messages))
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        return value


class ToolsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.tools = Tools(self.root)

    def test_rules_and_line_numbers(self):
        (self.root / 'a.py').write_text('def f(x=[]):\n    try:\n        eval("1")\n    except:\n        pass\n')
        findings = self.tools.analyze_python('a.py')['findings']
        self.assertEqual([(f['line'], f['rule']) for f in findings],
                         [(1, 'mutable-default'), (3, 'dynamic-execution'), (4, 'bare-except')])

    def test_syntax_error(self):
        (self.root / 'a.py').write_text('def :')
        self.assertEqual(self.tools.analyze_python('a.py')['findings'][0]['rule'], 'syntax-error')

    def test_keyword_default(self):
        (self.root / 'a.py').write_text('async def f(*, x={}):\n    return x\n')
        self.assertEqual(len(self.tools.analyze_python('a.py')['findings']), 1)

    def test_path_escape_and_hidden(self):
        for path in ['../outside.py', '/etc/passwd', '.env', '.git/config']:
            with self.subTest(path=path):
                self.assertFalse(self.tools.call('read_file', json.dumps({'path': path}))['ok'])

    def test_symlink_escape(self):
        (self.root / 'link.py').symlink_to(self.root.parent / 'outside.py')
        with self.assertRaises(ValueError):
            self.tools.resolve('link.py')

    def test_bad_parameters_and_tool(self):
        for name, args in [('exec', '{}'), ('read_file', '{'), ('read_file', '[]'),
                           ('read_file', '{"path":1}'), ('read_file', '{"path":"a.py","x":1}')]:
            self.assertFalse(self.tools.call(name, args)['ok'])

    def test_large_and_non_utf8(self):
        (self.root / 'large.py').write_bytes(b'a' * (MAX_BYTES + 1))
        (self.root / 'binary.py').write_bytes(b'\xff')
        for name in ['large.py', 'binary.py', 'missing.py']:
            self.assertFalse(self.tools.call('read_file', json.dumps({'path': name}))['ok'])

    def test_list_and_clean_example(self):
        t = Tools(ROOT)
        self.assertIn('examples/', t.list_files('.')['files'])
        self.assertEqual(t.analyze_python('examples/fixed.py')['findings'], [])
        self.assertTrue(t.read_file('examples/buggy.py')['content'].startswith('1:'))


class AgentTest(unittest.TestCase):
    def test_tool_cycle_and_followup_memory(self):
        client = ScriptClient([call(), {'content': '发现问题'}, {'content': '进一步解释'}])
        agent = Agent(client, Tools(ROOT))
        self.assertEqual(agent.run('审查'), '发现问题')
        self.assertEqual(client.requests[1][-1]['tool_call_id'], 'c1')
        self.assertTrue(json.loads(client.requests[1][-1]['content'])['ok'])
        agent.run('为什么')
        self.assertTrue(any(m.get('content') == '发现问题' for m in client.requests[2]))
        agent.reset()
        self.assertEqual(agent.history, [])

    def test_failed_turn_does_not_corrupt_history(self):
        client = ScriptClient([{'content': '好'}, call(), LLMError('断线')])
        agent = Agent(client, Tools(ROOT))
        agent.run('一')
        before = copy.deepcopy(agent.history)
        with self.assertRaises(LLMError):
            agent.run('二')
        self.assertEqual(before, agent.history)

    def test_loop_limit(self):
        agent = Agent(ScriptClient([call(), call()]), Tools(ROOT), max_steps=2)
        with self.assertRaises(LLMError):
            agent.run('循环')
        self.assertEqual(agent.history, [])

    def test_tool_error_is_returned_to_model(self):
        client = ScriptClient([call(arguments='{'), {'content': '参数错误已发现'}])
        Agent(client, Tools(ROOT)).run('审查')
        self.assertFalse(json.loads(client.requests[1][-1]['content'])['ok'])

    def test_whole_turn_trimming(self):
        agent = Agent(ScriptClient([{'content': str(i)} for i in range(5)]), Tools(ROOT), memory_turns=2)
        for i in range(5):
            agent.run(str(i))
        self.assertEqual(len(agent.history), 2)
        self.assertEqual(agent.history[0][0]['content'], '3')

    def test_malformed_messages(self):
        for value in [{}, {'tool_calls': 'bad'}, {'tool_calls': [{'id': 'a'}]}, {'content': 7}]:
            with self.subTest(value=value), self.assertRaises(LLMError):
                Agent(ScriptClient([value]), Tools(ROOT)).run('检查')

    def test_demo_uses_real_analysis(self):
        output = Agent(DemoClient(), Tools(ROOT)).run('演示')
        self.assertIn('mutable-default', output)
        self.assertIn('未调用 LLM', output)


class TransportTest(unittest.TestCase):
    def client(self):
        return Client('test-key', 'test-model')

    def response(self, value):
        return io.BytesIO(json.dumps(value).encode())

    @patch('code_review_agent.llm.time.sleep')
    @patch('code_review_agent.llm.urllib.request.urlopen')
    def test_retry_and_request_protocol(self, opener, sleep):
        opener.side_effect = [HTTPError('url', 429, 'rate', {}, None),
                              self.response({'choices': [{'message': {'content': 'done'}}]})]
        self.assertEqual(self.client().complete([{'role': 'user', 'content': '检查'}], [])['content'], 'done')
        request = opener.call_args.args[0]
        self.assertEqual(json.loads(request.data)['model'], 'test-model')
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-key')
        self.assertEqual(opener.call_count, 2)
        sleep.assert_called_once_with(0.5)

    @patch('code_review_agent.llm.urllib.request.urlopen')
    def test_auth_error_no_retry_or_key_leak(self, opener):
        opener.side_effect = HTTPError('url', 401, 'test-key', {}, None)
        with self.assertRaises(LLMError) as ctx:
            self.client().complete([], [])
        self.assertNotIn('test-key', str(ctx.exception))
        self.assertEqual(opener.call_count, 1)

    @patch('code_review_agent.llm.time.sleep')
    @patch('code_review_agent.llm.urllib.request.urlopen', side_effect=URLError('offline'))
    def test_network_retry_exhaustion(self, opener, sleep):
        with self.assertRaises(LLMError):
            self.client().complete([], [])
        self.assertEqual(opener.call_count, 3)

    @patch('code_review_agent.llm.urllib.request.urlopen')
    def test_bad_json(self, opener):
        opener.return_value = io.BytesIO(b'not json')
        with self.assertRaises(LLMError):
            self.client().complete([], [])

    def test_configuration(self):
        for key, model, url in [('', 'x', 'https://example.com'),
                                ('x', '', 'https://example.com'), ('x', 'x', 'http://example.com')]:
            with self.assertRaises(ValueError):
                Client(key, model, url)


if __name__ == '__main__':
    unittest.main()
