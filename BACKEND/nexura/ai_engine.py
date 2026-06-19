from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

import anthropic

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
        self.client = anthropic.AsyncAnthropic(
            api_key=config.ANTHROPIC_API_KEY
        )
        self.model = config.ANTHROPIC_MODEL
        self._ready = bool(config.ANTHROPIC_API_KEY)

    @property
    def is_ready(self) -> bool:
        return self._ready

    def _tool_definitions(self) -> list:
        return [
            {
                "name": "run_nmap",
                "description": "Port skanerlash va xizmatlarni aniqlash. Target domen yoki IP bo'lishi mumkin.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Domen yoki IP manzil"},
                        "fast": {"type": "boolean", "description": "Tez skanerlash (faqat keng tarqalgan portlar)", "default": True},
                    },
                    "required": ["target"],
                },
            },
            {
                "name": "run_nuclei",
                "description": "CVE va keng tarqalgan zaifliklarni qidirish.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "URL yoki domen"},
                        "severity": {"type": "string", "description": "low,medium,high,critical (vergul bilan)", "default": "medium,high,critical"},
                    },
                    "required": ["target"],
                },
            },
            {
                "name": "run_nikto",
                "description": "Web server konfiguratsiya zaifliklarini tekshiradi.",
                "input_schema": {
                    "type": "object",
                    "properties": {"target": {"type": "string", "description": "Target domen yoki URL"}},
                    "required": ["target"],
                },
            },
            {
                "name": "run_whatweb",
                "description": "Sayt texnologiyalarini (CMS, server, framework) aniqlaydi.",
                "input_schema": {
                    "type": "object",
                    "properties": {"target": {"type": "string", "description": "Target domen yoki URL"}},
                    "required": ["target"],
                },
            },
            {
                "name": "run_sqlmap",
                "description": "SQL injection zaifligini tekshiradi. Target parametrli URL bo'lishi kerak.",
                "input_schema": {
                    "type": "object",
                    "properties": {"target": {"type": "string", "description": "To'liq URL (masalan: http://example.com/page?id=1)"}},
                    "required": ["target"],
                },
            },
            {
                "name": "run_gobuster",
                "description": "Yashirin direktoriya va fayllarni qidiradi.",
                "input_schema": {
                    "type": "object",
                    "properties": {"target": {"type": "string", "description": "Base URL"}},
                    "required": ["target"],
                },
            },
            {
                "name": "run_amass",
                "description": "Subdomenlarni qidiradi.",
                "input_schema": {
                    "type": "object",
                    "properties": {"target": {"type": "string", "description": "Domen nomi"}},
                    "required": ["target"],
                },
            },
        ]

    def _system_prompt(self) -> str:
        return (
            "Sen NEXURA — AI kiberxavfsizlik skaneri yordamchisisisan.\n"
            "Foydalanuvchi bilan o'zbek tilida do'stona va tabiiy suhbatlashasan.\n\n"
            "QOIDALAR:\n"
            "1. Agar foydalanuvchi shunchaki salomlashsa yoki oddiy savol bersa, oddiy suhbat qil.\n"
            "2. Agar biror domen/IP ni tekshirish so'ralsa, mos tool'ni tanlab ishga tushir.\n"
            "3. Natijalarni ko'rib, agar chuqurroq tekshiruv kerak bo'lsa, yana tool chaqir.\n"
            "4. Yakunda topilgan zaifliklarni tushunarli, qisqa va aniq o'zbek tilida tushuntir.\n"
            "5. Agar natija bo'lmasa, boshqa tool bilan qayta tekshirib ko'r.\n"
            "6. Faqat task yakunlanganda yoki foydalanuvchi boshqa savol bersa, matnli javob qaytar.\n"
            "7. Xavfsizlik: faqat ruxsat etilgan tizimlarni tekshirish kerakligini eslat.\n"
        )

    async def chat(self, user_message: str, conversation_history: list | None = None) -> dict:
        if not self._ready:
            return {
                "response": "AI yordamchisi sozlanmagan. ANTHROPIC_API_KEY ni .env faylga qo'shing.",
                "tool_calls": [],
                "history": conversation_history or [],
            }

        messages = conversation_history or []
        messages.append({"role": "user", "content": user_message})

        tool_calls_made = []
        max_iterations = 6

        for iteration in range(max_iterations):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=self._system_prompt(),
                    tools=self._tool_definitions(),
                    messages=messages,
                )
            except Exception as e:
                logger.error("Claude API error: %s", e, exc_info=True)
                return {
                    "response": f"AI bilan aloqa xatosi: {str(e)[:200]}",
                    "tool_calls": tool_calls_made,
                    "history": messages,
                }

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                final_text = "".join(
                    block.text for block in response.content if block.type == "text"
                )
                return {
                    "response": final_text or "Tekshiruv yakunlandi.",
                    "tool_calls": tool_calls_made,
                    "history": messages,
                }

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_calls_made.append({"tool": tool_name, "input": dict(tool_input)})

                    result = await self._execute_tool(tool_name, tool_input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)[:4000],
                    })

            messages.append({"role": "user", "content": tool_results})

        return {
            "response": "Skanerlash juda uzoq davom etdi. Iltimos, qaytadan urinib ko'ring.",
            "tool_calls": tool_calls_made,
            "history": messages,
        }

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        from nexura.runner import ScanRunner

        runner = ScanRunner()

        method = getattr(runner, tool_name, None)
        if not method:
            return f"Noma'lum tool: {tool_name}"

        try:
            if asyncio.iscoroutinefunction(method):
                result = await method(**tool_input)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    runner._executor, lambda: method(**tool_input)
                )

            output = json.dumps(result, ensure_ascii=False, default=str)
            return output[:4000]
        except Exception as e:
            logger.error("Tool %s error: %s", tool_name, e, exc_info=True)
            return f"Xato: {str(e)[:200]}"

    def close(self):
        pass
