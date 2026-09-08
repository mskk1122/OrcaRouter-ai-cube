"""OrcaRouter HTTP adapter. No SDK, automatic retries, or transcript logging."""

import base64
import io
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import wave


class ProviderError(RuntimeError):
    """Safe error message: never contains provider body, API key or audio."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward credentials to a redirected host.
        return None


def validate_wav(data):
    try:
        with wave.open(io.BytesIO(data), 'rb') as f:
            if (f.getnchannels() not in (1, 2) or f.getsampwidth() != 2
                    or f.getframerate() not in (8000, 16000, 22050, 24000, 32000, 44100, 48000)
                    or not 0 < f.getnframes() <= f.getframerate() * 120):
                raise ValueError('Unsupported WAV')
            if len(f.readframes(f.getnframes())) != f.getnframes() * f.getnchannels() * 2:
                raise ValueError('Truncated WAV')
    except (wave.Error, EOFError, ValueError) as exc:
        raise ProviderError('Invalid PCM16 WAV audio') from None
    return data


class OrcaClient:
    def __init__(self, key, base_url='https://api.orcarouter.ai/v1',
                 model='google/gemini-2.5-flash', tts_model='openai/tts-1',
                 voice='alloy', timeout=45, opener=None):
        parsed = urllib.parse.urlsplit(base_url)
        if (not key.strip() or parsed.scheme != 'https' or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ValueError('API key and HTTPS base URL required')
        if not 1 <= timeout <= 120:
            raise ValueError('API timeout must be between 1 and 120 seconds')
        self.key, self.base = key.strip(), base_url.rstrip('/')
        self.model, self.tts_model, self.voice = model, tts_model, voice
        self.timeout = timeout
        self.open = opener

    def _post(self, route, payload, limit):
        if self.open is None:
            # Separate, cancellable process bounds DNS, TLS, headers and slow bodies.
            # Credentials travel over stdin, never command arguments or a file.
            envelope = dict(url=self.base + route, key=self.key, payload=payload,
                            timeout=self.timeout, limit=limit)
            try:
                completed = subprocess.run(
                    [sys.executable, '-m', 'ai_cube.http_worker'],
                    input=json.dumps(envelope).encode(), capture_output=True,
                    timeout=self.timeout, check=False)
            except subprocess.TimeoutExpired:
                raise ProviderError('OrcaRouter request timed out') from None
            except OSError:
                raise ProviderError('Cannot start OrcaRouter request worker') from None
            if completed.returncode:
                message = completed.stderr.decode('ascii', errors='replace').strip()
                # Worker writes safe diagnostics only; never propagate tracebacks.
                if not message.startswith('OrcaRouter '):
                    message = 'OrcaRouter request worker failed'
                raise ProviderError(message[:120])
            if len(completed.stdout) > limit:
                raise ProviderError('OrcaRouter response exceeds size limit')
            return completed.stdout
        request = urllib.request.Request(
            self.base + route, data=json.dumps(payload).encode('utf-8'),
            headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json'},
            method='POST')
        try:
            with self.open(request, timeout=self.timeout) as response:
                result = response.read(limit + 1)
        except urllib.error.HTTPError as exc:
            raise ProviderError('OrcaRouter HTTP %d' % exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ProviderError('OrcaRouter connection failed or timed out') from None
        if len(result) > limit:
            raise ProviderError('OrcaRouter response exceeds size limit')
        return result

    def answer(self, wav):
        validate_wav(wav)
        if len(wav) > 500_000:
            raise ProviderError('Recording exceeds 12 second input budget')
        payload = {
            'model': self.model, 'max_tokens': 240,
            'messages': [
                {'role': 'system', 'content':
                 '너는 책상 위의 작은 친구 AI 큐브야. 사용자의 음성을 듣고 자연스러운 한국어로 '
                 '다정하고 정확하게 답해. 기본적으로 1~3문장, 200자 이내로 짧게 말해. '
                 '마크다운, 이모지, 표, 음성 전사문을 출력하지 마. '
                 '말을 알아듣지 못했다면 다시 말해 달라고 해. 들리지 않은 내용을 지어내지 마.'},
                {'role': 'user', 'content': [
                    {'type': 'text', 'text': '이 음성의 사용자에게 답해 줘.'},
                    {'type': 'input_audio', 'input_audio': {
                        'data': base64.b64encode(wav).decode('ascii'), 'format': 'wav'}}]}]}
        raw = self._post('/chat/completions', payload, 128_000)
        try:
            text = json.loads(raw)['choices'][0]['message']['content']
            if not isinstance(text, str) or not text.strip():
                raise ValueError()
        except (ValueError, KeyError, TypeError, IndexError):
            raise ProviderError('OrcaRouter returned no usable answer') from None
        return text.strip()[:600]

    def speak(self, text):
        raw = self._post('/audio/speech', {
            'model': self.tts_model, 'voice': self.voice,
            'input': text, 'response_format': 'wav'}, 12_000_000)
        return validate_wav(raw)
