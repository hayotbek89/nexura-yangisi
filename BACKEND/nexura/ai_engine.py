from __future__ import annotations

import asyncio
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from nexura import config

logger = logging.getLogger(__name__)


_engine_instance: AIEngine | None = None


def get_engine() -> AIEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AIEngine()
    return _engine_instance


class AIEngine:
    def __init__(self):
        self._llm = None
        self._ready = False
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._load_model()

    def _load_model(self):
        model_path = Path(config.LLAMA_MODEL_PATH)
        if not model_path.exists():
            return

        try:
            from llama_cpp import Llama

            self._llm = Llama(
                model_path=str(model_path),
                n_ctx=config.LLAMA_N_CTX,
                n_threads=config.LLAMA_N_THREADS,
                n_gpu_layers=config.LLAMA_N_GPU_LAYERS,
                verbose=False,
            )
            self._ready = True
        except Exception as e:
            logger.error("AI Engine load error: %s", e, exc_info=True)
            self._ready = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    def ask(self, system: str, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        return self._call_llm(system, prompt, config.TIMEOUT, temperature, max_tokens)

    def ask_with_timeout(self, system: str, prompt: str, timeout: float = 60.0) -> str:
        return self._call_llm(system, prompt, timeout, config.LLAMA_TEMP, config.LLAMA_MAX_TOKENS)

    def _call_llm(self, system: str, prompt: str, timeout: float,
                  temperature: float = None, max_tokens: int = None) -> str:
        if not self._ready:
            msg = "AI Engine yoqilmagan. GGUF model faylini LOCAL_AI_MODELS/ papkasiga joylashtiring."
            raise RuntimeError(msg)

        import concurrent.futures

        fut = self._executor.submit(
            self._llm.create_chat_completion,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature or config.LLAMA_TEMP,
            max_tokens=max_tokens or config.LLAMA_MAX_TOKENS,
        )
        try:
            resp = fut.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise RuntimeError(f"AI model did not respond within {timeout}s")
        except Exception as e:
            logger.error("AI response parsing error: %s", e, exc_info=True)
            raise RuntimeError(f"AI response format error: {type(e).__name__}: {str(e)[:100]}")

        try:
            if isinstance(resp, dict) and "choices" in resp and len(resp["choices"]) > 0:
                choice = resp["choices"][0]
                if isinstance(choice, dict) and "message" in choice:
                    message = choice["message"]
                    if isinstance(message, dict) and "content" in message:
                        return message["content"].strip()
            raise KeyError("Unexpected response structure from llama-cpp-python")
        except (KeyError, IndexError, TypeError) as e:
            logger.error("Failed to extract content from AI response: %s\nResponse: %s", e, resp, exc_info=True)
            raise ValueError(f"AI response format mismatch: {str(e)[:100]}")

    def ask_structured(self, system: str, prompt: str) -> dict:
        raw = self.ask(system, prompt)
        return self._extract_json(raw)

    async def ask_async(self, system: str, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        return await asyncio.to_thread(
            self.ask, system, prompt, temperature, max_tokens
        )

    async def ask_structured_async(self, system: str, prompt: str) -> dict:
        raw = await self.ask_async(system, prompt)
        return self._extract_json(raw)

    def _extract_json(self, text: str) -> dict:
        return extract_json(text)


def extract_json(text: str) -> dict:
    text = _strip_markdown_fence(text)
    candidate = _extract_json_object(text)
    if candidate is None:
        raise ValueError(f"Model JSON qaytarmadi yoki formati noto'g'ri:\n{text[:300]}")

    result = _try_parse(candidate)
    if result is not None:
        return result

    result = _try_parse(_fix_trailing_commas(candidate))
    if result is not None:
        return result

    result = _try_parse(_fix_unquoted_keys(candidate))
    if result is not None:
        return result

    result = _try_parse(_fix_single_quotes(candidate))
    if result is not None:
        return result

    result = _try_parse(_fix_single_quotes(_fix_unquoted_keys(_fix_trailing_commas(candidate))))
    if result is not None:
        return result

    logger.error("extract_json barcha urinishlar muvaffaqiyatsiz. AI xom javob:\n%s", text)
    raise ValueError(f"Model JSON qaytarmadi yoki formati noto'g'ri:\n{text[:300]}")


def _strip_markdown_fence(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return None


def _try_parse(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _fix_trailing_commas(text: str) -> str:
    result = re.sub(r",\s*}", "}", text)
    result = re.sub(r",\s*]", "]", result)
    return result


def _fix_unquoted_keys(text: str) -> str:
    result = re.sub(r"\{(\s*)([a-zA-Z_]\w*)\s*:", r'{\1"\2":', text)
    result = re.sub(r",\s*([a-zA-Z_]\w*)\s*:", r', "\1":', result)
    return result


_APOSTROPHE_PLACEHOLDER = "\x00"

def _protect_apostrophe(m):
    return m.group(1) + _APOSTROPHE_PLACEHOLDER + m.group(2)

def _fix_single_quotes(text: str) -> str:
    protected = re.sub(r"(\w)'(\w)", _protect_apostrophe, text)
    result = protected.replace("'", '"')
    result = result.replace(_APOSTROPHE_PLACEHOLDER, "'")
    return result


_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_SYSTEM_PROMPT_PATH = _PROMPTS_DIR / "system.txt"


def _load_system_prompt() -> str:
    try:
        if _SYSTEM_PROMPT_PATH.exists():
            return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        pass
    logger.warning("System prompt file not found, using fallback")
    return _FALLBACK_SYSTEM_PROMPT


SYSTEM_PROMPT = _load_system_prompt()


_FALLBACK_SYSTEM_PROMPT = (
    "Siz NEXURA — AI quvvatli zaiflik skaneri orchestratorisiz. "
    "Foydalanuvchi tabiiy tilda so'rov yozadi, siz JSON qaytarishingiz kerak.\n\n"
    "MAVJUD TOOL'LAR:\n"
    "- nmap: port skanerlash\n"
    "- nuclei: CVE zaiflik skaneri\n"
    "- nikto: web server zaifliklari\n"
    "- sqlmap: SQL injection\n"
    "- gobuster: directory brute-force\n"
    "- amass: subdomain topish\n"
    "- whatweb: texnologiyalarni aniqlash\n"
    "- network: tezkor Python port skaner\n\n"
    'JSON: {"target":"...", "intent":"...", "tools":[{"tool":"...", "args":["..."], "description":"..."}], "reasoning":"...", "agentic":true/false}\n'
    "FAQAT JSON, boshqa hech narsa yo'q.\n"
)

