from __future__ import annotations

import logging

import httpx

from nexura import config

logger = logging.getLogger(__name__)


async def send_to_n8n(message: str) -> dict:
    if not config.N8N_WEBHOOK_URL:
        return {
            "response": "n8n integratsiyasi sozlanmagan. "
                        "N8N_WEBHOOK_URL ni .env fayliga qo'shing.",
            "error": True,
        }

    try:
        async with httpx.AsyncClient(timeout=config.N8N_TIMEOUT) as client:
            resp = await client.post(
                config.N8N_WEBHOOK_URL,
                json={"message": message},
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
                        f"({config.N8N_TIMEOUT} soniyadan ortiq). "
                        "Qaytadan urinib ko'ring.",
            "error": True,
        }
    except httpx.HTTPStatusError as e:
        return {
            "response": f"n8n bilan aloqa xatosi: {e.response.status_code}",
            "error": True,
        }
    except Exception as e:
        logger.error("n8n client error: %s", e, exc_info=True)
        return {
            "response": f"Kutilmagan xato: {str(e)}",
            "error": True,
        }
