from __future__ import annotations

import logging

import httpx

from nexura import config

logger = logging.getLogger(__name__)


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
                f"{base_url.rstrip('/')}/api/generate",
                json={
                    "model": model,
                    "prompt": message,
                    "stream": False,
                },
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "response": data.get("response", "Javob olinmadi"),
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
