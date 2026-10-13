"""CLI entry point: python -m code_review_agent."""
import argparse
import os
from pathlib import Path
import sys
from .agent import Agent
from .demo import DemoClient
from .llm import Client, LLMError
from .tools import Tools


def main(argv=None):
    parser = argparse.ArgumentParser(description='代码审查 Agent（Python 3.10+，零第三方依赖）')
    parser.add_argument('prompt', nargs='?', help='审查问题；省略则进入交互模式')
    parser.add_argument('--root', default='.', help='允许读取的项目根目录')
    parser.add_argument('--demo', action='store_true', help='离线固定示例，不调用 LLM')
    parser.add_argument('--trace', action='store_true', help='向标准错误显示工具调用过程')
    parser.add_argument('--output', type=Path, help='保存 Markdown 报告（覆盖目标文件）')
    parser.add_argument('--max-steps', type=int, default=8)
    args = parser.parse_args(argv)
    try:
        client = DemoClient() if args.demo else Client(
            os.getenv('LLM_API_KEY', 'sk-16724762e627419993fe335ee73ba243'), os.getenv('LLM_MODEL', 'deepseek-chat'),
            os.getenv('LLM_BASE_URL', 'https://api.deepseek.com/v1'))
        agent = Agent(client, Tools(args.root), max_steps=args.max_steps,
                      trace=(lambda text: print(text, file=sys.stderr)) if args.trace else None)
        def run(prompt):
            result = agent.run(prompt)
            print(result)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(result + '\n', encoding='utf-8')
        if args.demo:
            print('离线演示模式：固定审查 examples/buggy.py，未调用大模型。', file=sys.stderr)
            run('审查 examples/buggy.py')
        elif args.prompt:
            run(args.prompt)
        else:
            print('代码审查 Agent。输入 /reset 清空记忆，/exit 退出。')
            while True:
                try:
                    prompt = input('\n你 > ').strip()
                except EOFError:
                    break
                if prompt == '/exit':
                    break
                if prompt == '/reset':
                    agent.reset()
                    print('已清空记忆。')
                    continue
                if not prompt:
                    continue
                try:
                    run(prompt)
                except (LLMError, ValueError, OSError) as exc:
                    print('错误：' + str(exc), file=sys.stderr)
        return 0
    except (LLMError, ValueError, OSError) as exc:
        print('错误：' + str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\n已退出。', file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
