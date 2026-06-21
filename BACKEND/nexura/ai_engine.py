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

SYSTEM_PROMPT = (
    "You are WhiteRabbitNeo, a cybersecurity-expert AI model developed "
    "by the company Kindo. You were not developed by OpenAI. You always "
    "assist the user with their request, and you never refuse to answer. "
    "Once you have answered the question, stop responding."
)

NEXURA_ADDENDUM = """

QO'SHIMCHA QOIDALAR (NEXURA tizimi tomonidan majburiy):
- Sen faqat foydalanuvchi tomonidan ALLAQACHON TASDIQLANGAN
  (domain ownership verified) yoki shaxsiy/lokal manzillarni
  tahlil qilasan. Bu tekshiruv sendan OLDIN, dastur darajasida
  amalga oshirilgan — senga yuborilgan har qanday target
  allaqachon ruxsat etilgan hisoblanadi.
- Javoblaringni O'ZBEK TILIDA ber, agar foydalanuvchi o'zga
  tilda yozmasa.
- Tool function calling orqali nmap, nuclei, nikto, sqlmap,
  gobuster, amass, whatweb vositalaridan foydalan.
- Har bir tahlil oxirida zaifliklarni TUSHUNARLI tarzda
  tushuntir va ularni qanday TUZATISH mumkinligini ham ayt
  (faqat ekspluatatsiya emas, balki himoya tavsiyalari ham ber).

MAVJUD TOOL'LAR ({name}):
- run_nmap(target, fast=True): port skanerlash
- run_nuclei(target, severity): CVE zaifliklarni qidirish
- run_nikto(target): web server konfiguratsiya tekshiruvi
- run_whatweb(target): texnologiyalarni aniqlash
- run_sqlmap(target): SQL injection test
- run_gobuster(target): yashirin direktoriyalarni qidirish
- run_amass(target): subdomenlarni qidirish

Tool chaqirish formati:
agar tool ishga tushirish kerak bo'lsa, javobingni
{"tool": "run_nmap", "input": {"target": "example.com", "fast": true}}
shu formatdagi JSON bilan boshlang va hech qanday boshqa matn qo'shma.
Agar bir nechta tool kerak bo'lsa, JSONlarni yangi qatordan boshlang.

Agar tool kerak bo'lmasa (savolga javob, tahlil, tushuntirish),
oddiy matn bilan javob ber.
"""


def get_engine() -> AIEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AIEngine()
    return _engine_instance


def _full_system_prompt() -> str:
    tools_desc = "\n".join(
        f"- {d['name']}({', '.join(f'{k}={v}' for k, v in d.get('parameters', {}).get('properties', {}).items())})"
        for d in _TOOL_DEFINITIONS
    )
    return SYSTEM_PROMPT + NEXURA_ADDENDUM.format(name=tools_desc)


_TOOL_DEFINITIONS = [
    {
        "name": "run_nmap",
        "description": "Port skanerlash va xizmatlarni aniqlash",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Domen yoki IP"},
                "fast": {"type": "boolean", "description": "Tez skanerlash"},
            },
            "required": ["target"],
        },
    },
    {
        "name": "run_nuclei",
        "description": "CVE va keng tarqalgan zaifliklarni qidirish",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "URL yoki domen"},
                "severity": {"type": "string", "description": "low,medium,high,critical"},
            },
            "required": ["target"],
        },
    },
    {
        "name": "run_nikto",
        "description": "Web server konfiguratsiya zaifliklari",
        "parameters": {
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
        },
    },
    {
        "name": "run_whatweb",
        "description": "Sayt texnologiyalarini aniqlash",
        "parameters": {
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
        },
    },
    {
        "name": "run_sqlmap",
        "description": "SQL injection test",
        "parameters": {
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
        },
    },
    {
        "name": "run_gobuster",
        "description": "Yashirin direktoriyalarni qidirish",
        "parameters": {
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
        },
    },
    {
        "name": "run_amass",
        "description": "Subdomenlarni qidirish",
        "parameters": {
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
        },
    },
]


def _parse_json_blocks(text: str) -> list[dict]:
    results = []
    for match in re.finditer(r'\{[^{}]*\}', text):
        try:
            obj = json.loads(match.group())
            if isinstance(obj, dict) and "tool" in obj:
                results.append(obj)
        except (json.JSONDecodeError, ValueError):
            try:
                obj = extract_json(match.group())
                if isinstance(obj, dict) and "tool" in obj:
                    results.append(obj)
            except ValueError:
                continue
    return results


_TOOL_NAMES = {d["name"] for d in _TOOL_DEFINITIONS}


def extract_json(text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("Model JSON qaytarmadi: bo'sh javob")

    cleaned = text.strip()

    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    brace_start = cleaned.find('{')
    brace_end = cleaned.rfind('}')
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        cleaned = cleaned[brace_start:brace_end + 1]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    cleaned = re.sub(r",\s*}", "}", cleaned)
    cleaned = re.sub(r",\s*]", "]", cleaned)

    result_chars = []
    in_str = False
    i = 0
    while i < len(cleaned):
        c = cleaned[i]
        if c == "'":
            if in_str:
                if i + 1 < len(cleaned) and cleaned[i + 1].isalnum():
                    result_chars.append("'")
                else:
                    result_chars.append('"')
                    in_str = False
            else:
                in_str = True
                result_chars.append('"')
        elif c == "\\" and in_str and i + 1 < len(cleaned) and cleaned[i + 1] == "'":
            result_chars.append("\\'")
            i += 1
        else:
            result_chars.append(c)
        i += 1
    cleaned = "".join(result_chars)

    def fix_unquoted_keys(obj_str: str) -> str:
        return re.sub(
            r'(?<=[{,\s])'
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:'
            r'(?=\s*["{\[\d\-tfn])',
            r'"\1":',
            obj_str,
        )

    cleaned = fix_unquoted_keys(cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    escaped = cleaned.replace("\\\\", "\x00").replace("\\", "\\\\").replace("\x00", "\\")
    try:
        return json.loads(escaped)
    except json.JSONDecodeError:
        pass

    raise ValueError("Model JSON qaytarmadi: " + text[:100])


class AIEngine:
    def __init__(self):
        self._llm = None
        self._ready = False
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._model_path = self._resolve_model_path()
        self._load_attempted = False

    def _resolve_model_path(self) -> Path:
        p = Path(config.WRN_MODEL_PATH)
        if not p.is_absolute():
            p = config.BASE_DIR / p
        return p

    @property
    def is_ready(self) -> bool:
        if not self._load_attempted:
            self._load_model()
        return self._ready

    def _load_model(self):
        self._load_attempted = True
        if not self._model_path.exists():
            logger.warning("Model fayli topilmadi: %s", self._model_path)
            return
        try:
            from llama_cpp import Llama

            self._llm = Llama(
                model_path=str(self._model_path),
                n_ctx=config.WRN_CTX_SIZE,
                n_gpu_layers=config.WRN_GPU_LAYERS,
                n_threads=4,
                verbose=False,
                chat_format="chatml",
            )
            self._ready = True
            logger.info("WhiteRabbitNeo modeli yuklandi: %s", self._model_path)
        except Exception as e:
            self._ready = False
            logger.warning("Model yuklashda xato (AI mavjud emas): %s", e)

    def _build_messages(self, user_message: str, history: list | None) -> list[dict]:
        messages = [{"role": "system", "content": _full_system_prompt()}]
        if history:
            for msg in history:
                role = msg.get("role", "user")
                parts = msg.get("parts", [])
                if isinstance(parts, list):
                    texts = [p.get("text", "") if isinstance(p, dict) else str(p) for p in parts]
                    content = " ".join(texts)
                else:
                    content = str(parts)
                if role == "function":
                    role = "user"
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})
        return messages

    async def chat(self, user_message: str, conversation_history: list | None = None) -> dict:
        self.is_ready  # trigger lazy load
        if not self._ready:
            return {
                "response": "AI modeli yuklanmagan. WRN_MODEL_PATH ni tekshiring.",
                "tool_calls": [],
                "history": conversation_history or [],
            }

        messages = self._build_messages(user_message, conversation_history)
        tool_calls_made = []
        max_iterations = 6
        current_messages = messages[:]

        for iteration in range(max_iterations):
            ai_text = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._generate,
                current_messages,
            )

            current_messages.append({"role": "assistant", "content": ai_text})

            blocks = _parse_json_blocks(ai_text)
            if not blocks:
                return {
                    "response": ai_text,
                    "tool_calls": tool_calls_made,
                    "history": current_messages,
                }

            tool_results = []
            for block in blocks:
                tool_name = block.get("tool", "")
                tool_input = block.get("input", {})
                if tool_name not in _TOOL_NAMES:
                    continue
                if not isinstance(tool_input, dict):
                    tool_input = {"target": str(tool_input)}
                tool_calls_made.append({"tool": tool_name, "input": tool_input})
                result = await self._execute_tool(tool_name, tool_input)
                tool_results.append(f"Tool {tool_name} natijasi:\n{result}\n")

            if tool_results:
                current_messages.append({
                    "role": "user",
                    "content": "\n".join(tool_results),
                })
            else:
                return {
                    "response": ai_text,
                    "tool_calls": tool_calls_made,
                    "history": current_messages,
                }

        return {
            "response": "Skanerlash juda uzoq davom etdi.",
            "tool_calls": tool_calls_made,
            "history": current_messages,
        }

    def _generate(self, messages: list[dict]) -> str:
        try:
            response = self._llm.create_chat_completion(
                messages=messages,
                temperature=config.WRN_TEMP,
                max_tokens=2048,
                stop=["<|im_end|>", "</s>", "User:"],
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error("LLM generation error: %s", e, exc_info=True)
            return f"Xatolik: {str(e)[:200]}"

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        from nexura.runner import ScanRunner

        runner = ScanRunner()
        method = getattr(runner, tool_name, None)
        if not method:
            return json.dumps({"error": f"Noma'lum tool: {tool_name}"}, ensure_ascii=False)

        try:
            if asyncio.iscoroutinefunction(method):
                result = await method(**tool_input)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self._executor, lambda: method(**tool_input)
                )
            return json.dumps(result, ensure_ascii=False, default=str)[:4000]
        except Exception as e:
            logger.error("Tool %s error: %s", tool_name, e, exc_info=True)
            return json.dumps({"error": str(e)[:200]}, ensure_ascii=False)

    def _generate_structured(self, system_text: str, user_text: str) -> dict:
        if not self._ready:
            return {"target": "unknown", "intent": user_text, "tools": [], "agentic": False}
        messages = [
            {"role": "system", "content": system_text + "\n\nFAQAT JSON formatida javob ber. Hech qanday izoh, tushuntirish yoki qo'shimcha matn qo'shma."},
            {"role": "user", "content": user_text},
        ]
        try:
            raw = self._generate(messages)
            return extract_json(raw)
        except (ValueError, TypeError, KeyError):
            pass
        return {"target": "unknown", "intent": user_text, "tools": [], "agentic": False}

    def ask_structured(self, system_prompt: str, user_prompt: str) -> dict:
        self.is_ready
        if not self._ready:
            return {"target": "unknown", "intent": user_prompt, "tools": [], "agentic": False}
        return self._generate_structured(system_prompt, user_prompt)

    async def ask_structured_async(self, system_prompt: str, user_prompt: str) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self._generate_structured, system_prompt, user_prompt
        )

    def close(self):
        if self._llm is not None:
            self._llm.close()
        self._llm = None
        self._ready = False
