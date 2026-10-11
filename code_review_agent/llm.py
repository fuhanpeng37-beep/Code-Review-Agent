"""OpenAI-compatible Chat Completions transport using Python's standard library."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request


class LLMError(RuntimeError):
    pass


class Client:
    def __init__(self, api_key, model, base_url='https://api.openai.com/v1', retries=2, timeout=45):
        if not api_key or not model:
            raise ValueError('请设置 LLM_API_KEY 和 LLM_MODEL，或使用 --demo')
        parsed = urllib.parse.urlparse(base_url)
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in {'localhost', '127.0.0.1', '::1'}):
            raise ValueError('远程 API 必须使用 HTTPS')
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('API 地址不能包含凭据、查询参数或片段')
        self.api_key, self.model = api_key, model
        self.url = base_url.rstrip('/') + '/chat/completions'
        self.retries, self.timeout = retries, timeout

    def complete(self, messages, tools):
        body = json.dumps({'model': self.model, 'messages': messages,
                           'tools': tools, 'tool_choice': 'auto'}, ensure_ascii=False).encode()
        request = urllib.request.Request(self.url, data=body, headers={
            'Authorization': 'Bearer ' + self.api_key, 'Content-Type': 'application/json'})
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    data = json.loads(response.read(2_000_001))
                message = data['choices'][0]['message']
                if not isinstance(message, dict):
                    raise TypeError('message')
                return message
            except urllib.error.HTTPError as exc:
                status = exc.code
                exc.close()
                if status not in {408, 429, 500, 502, 503, 504} or attempt == self.retries:
                    raise LLMError(f'API 请求失败 (HTTP {status})；请检查地址、权限、配额和模型。') from None
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
                if attempt == self.retries:
                    raise LLMError('API 网络连接失败或超时，请检查网络后重试。') from None
            except (ValueError, KeyError, IndexError, TypeError):
                raise LLMError('API 响应格式不符合 Chat Completions 协议。') from None
            time.sleep(0.5 * (2 ** attempt))
