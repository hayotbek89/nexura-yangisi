from __future__ import annotations

import logging

import httpx

from nexura import config

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "Siz NEXURA AI Security Scanner yordamchisisiz. "
    "Sizning vazifangiz kiberxavfsizlik bo'yicha yordam berish."
    "FAQAT O'ZBEK TILIDA javob bering. Hech qachon ingliz tilida javob bermang. "
    "Agar foydalanuvchi boshqa tilda so'rasa ham, siz o'zbek tilida javob berishingiz kerak. "
    "Professional cybersecurity mutaxassisi sifatida xavfsizlik maslahatlari bering."
)


async def ask_ollama(message: str) -> dict:
    base_url = config.OLLAMA_BASE_URL
    model = config.OLLAMA_MODEL

    if not base_url:
        return {
            "response": "Ollama integratsiyasi sozlanmagan. "
                        "OLLAMA_BASE_URL ni .env fayliga qo'shing.",
            "error": True,
        }

    try:
        async with httpx.AsyncClient(timeout=config.OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": message},
                    ],
                    "stream": False,
                },
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            msg = data.get("message", {})
            return {
                "response": msg.get("content", "Javob olinmadi"),
                "error": False,
            }
    except httpx.TimeoutException:
        return {
            "response": "AI javob berishda juda uzoq vaqt oldi "
                        f"({config.OLLAMA_TIMEOUT} soniyadan ortiq). "
                        "Qaytadan urinib ko'ring.",
            "error": True,
        }
    except httpx.HTTPStatusError as e:
        return {
            "response": f"Ollama bilan aloqa xatosi: {e.response.status_code}",
            "error": True,
        }
    except Exception as e:
        logger.error("ollama client error: %s", e, exc_info=True)
        return {
            "response": f"Kutilmagan xato: {str(e)}",
            "error": True,
        }
