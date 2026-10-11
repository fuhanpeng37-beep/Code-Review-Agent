import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CLITest(unittest.TestCase):
    def run_cli(self, *args, env=None):
        return subprocess.run([sys.executable, '-m', 'code_review_agent', *args],
                              cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)

    def test_demo_export_and_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.md'
            result = self.run_cli('--demo', '--trace', '--output', str(path))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_text(encoding='utf-8'), result.stdout)
            self.assertIn('read_file', result.stderr)
            self.assertIn('analyze_python', result.stderr)
            self.assertIn('dynamic-execution', result.stdout)

    def test_missing_credentials(self):
        env = {k: v for k, v in os.environ.items() if k not in {'LLM_API_KEY', 'LLM_MODEL'}}
        result = self.run_cli('审查文件', env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn('LLM_API_KEY', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_bad_root(self):
        result = self.run_cli('--demo', '--root', '/nonexistent-homework-agent-directory')
        self.assertEqual(result.returncode, 1)
        self.assertIn('工作目录不存在', result.stderr)


if __name__ == '__main__':
    unittest.main()
