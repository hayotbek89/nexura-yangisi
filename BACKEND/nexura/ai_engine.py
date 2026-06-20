from __future__ import annotations

import asyncio
import json
import logging

import google.generativeai as genai

from nexura import config

logger = logging.getLogger(__name__)

_engine_instance: AIEngine | None = None


def get_engine() -> AIEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AIEngine()
    return _engine_instance


def _make_tools() -> list[dict]:
    return [{
        "function_declarations": [
            {
                "name": "run_nmap",
                "description": "Port skanerlash va xizmatlarni aniqlash. Target domen yoki IP bo'lishi mumkin.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Domen yoki IP manzil"},
                        "fast": {"type": "boolean", "description": "Tez skanerlash", "default": True},
                    },
                    "required": ["target"],
                },
            },
            {
                "name": "run_nuclei",
                "description": "CVE va keng tarqalgan zaifliklarni qidirish.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "URL yoki domen"},
                        "severity": {"type": "string", "description": "low,medium,high,critical", "default": "medium,high,critical"},
                    },
                    "required": ["target"],
                },
            },
            {
                "name": "run_nikto",
                "description": "Web server konfiguratsiya zaifliklarini tekshiradi.",
                "parameters": {
                    "type": "object",
                    "properties": {"target": {"type": "string", "description": "Target domen yoki URL"}},
                    "required": ["target"],
                },
            },
            {
                "name": "run_whatweb",
                "description": "Sayt texnologiyalarini (CMS, server, framework) aniqlaydi.",
                "parameters": {
                    "type": "object",
                    "properties": {"target": {"type": "string", "description": "Target domen yoki URL"}},
                    "required": ["target"],
                },
            },
            {
                "name": "run_sqlmap",
                "description": "SQL injection zaifligini tekshiradi. Target parametrli URL bo'lishi kerak.",
                "parameters": {
                    "type": "object",
                    "properties": {"target": {"type": "string", "description": "To'liq URL (masalan: http://example.com/page?id=1)"}},
                    "required": ["target"],
                },
            },
            {
                "name": "run_gobuster",
                "description": "Yashirin direktoriya va fayllarni qidiradi.",
                "parameters": {
                    "type": "object",
                    "properties": {"target": {"type": "string", "description": "Base URL"}},
                    "required": ["target"],
                },
            },
            {
                "name": "run_amass",
                "description": "Subdomenlarni qidiradi.",
                "parameters": {
                    "type": "object",
                    "properties": {"target": {"type": "string", "description": "Domen nomi"}},
                    "required": ["target"],
                },
            },
        ]
    }]


class AIEngine:
    def __init__(self):
        api_key = config.GEMINI_API_KEY
        self._ready = bool(api_key)
        self.model = None
        if self._ready:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                model_name=config.GEMINI_MODEL,
                system_instruction=self._system_prompt(),
                tools=_make_tools(),
            )

    @property
    def is_ready(self) -> bool:
        return self._ready

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
                "response": "AI yordamchisi sozlanmagan. GEMINI_API_KEY ni .env faylga qo'shing.",
                "tool_calls": [],
                "history": conversation_history or [],
            }

        contents = conversation_history or []
        contents.append({"role": "user", "parts": [{"text": user_message}]})

        tool_calls_made = []
        max_iterations = 6

        for _iteration in range(max_iterations):
            try:
                response = await asyncio.to_thread(
                    self.model.generate_content, contents
                )
            except Exception as e:
                logger.error("Gemini API error: %s", e, exc_info=True)
                return {
                    "response": f"AI bilan aloqa xatosi: {str(e)[:200]}",
                    "tool_calls": tool_calls_made,
                    "history": contents,
                }

            candidate = response.candidates[0] if response.candidates else None
            if not candidate:
                contents.append({"role": "model", "parts": [{"text": "Javob topilmadi."}]})
                return {
                    "response": "Javob topilmadi.",
                    "tool_calls": tool_calls_made,
                    "history": contents,
                }

            parts = candidate.content.parts

            function_calls = [p for p in parts if p.function_call]
            text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]

            if not function_calls:
                final_text = " ".join(text_parts) or "Tekshiruv yakunlandi."
                contents.append({"role": "model", "parts": [{"text": final_text}]})
                return {
                    "response": final_text,
                    "tool_calls": tool_calls_made,
                    "history": contents,
                }

            model_parts = []
            function_response_parts = []
            for fc_part in function_calls:
                fc = fc_part.function_call
                tool_name = fc.name
                tool_input = {k: v for k, v in fc.args.items()}
                model_parts.append({"function_call": {"name": tool_name, "args": tool_input}})
                tool_calls_made.append({"tool": tool_name, "input": tool_input})

                result = await self._execute_tool(tool_name, tool_input)

                function_response_parts.append({
                    "function_response": {"name": tool_name, "response": {"result": result}},
                })

            if text_parts:
                model_parts.append({"text": " ".join(text_parts)})
            contents.append({"role": "model", "parts": model_parts})
            contents.append({"role": "function", "parts": function_response_parts})

        return {
            "response": "Skanerlash juda uzoq davom etdi. Iltimos, qaytadan urinib ko'ring.",
            "tool_calls": tool_calls_made,
            "history": contents,
        }

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
                    runner._executor, lambda: method(**tool_input)
                )
            return json.dumps(result, ensure_ascii=False, default=str)[:4000]
        except Exception as e:
            logger.error("Tool %s error: %s", tool_name, e, exc_info=True)
            return json.dumps({"error": str(e)[:200]}, ensure_ascii=False)

    def close(self):
        pass
