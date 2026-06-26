from __future__ import annotations

import logging
import re

import httpx

from nexura import config

logger = logging.getLogger(__name__)

# Uzbek-specific characters for language detection
UZBEK_PATTERN = re.compile(r"[ғҒҳҲқҚўЎқҚчЧшШёЁюЮяЯа-я]", re.IGNORECASE)
RUSSIAN_PATTERN = re.compile(r"[ёЁъЪэЭюЮяЯа-я]", re.IGNORECASE)
CYRILLIC_PATTERN = re.compile(r"[а-яА-ЯёЁғҒҳҲқҚўЎ]", re.IGNORECASE)


def _detect_lang(text: str) -> str:
    """Detect if text is Uzbek, Russian, English, or other."""
    if not text.strip():
        return "uz"
    # Strong Uzbek indicators
    uz_specific = {"ғ", "Ғ", "ҳ", "Ҳ", "қ", "Қ", "ў", "Ў"}
    if any(c in text for c in uz_specific):
        return "uz"
    # Check Cyrillic
    cyril_chars = len(CYRILLIC_PATTERN.findall(text))
    total_chars = len(re.sub(r"\s", "", text))
    if total_chars > 0 and cyril_chars / total_chars > 0.1:
        # Check for Russian-specific characters
        rus_chars = len(RUSSIAN_PATTERN.findall(text))
        uz_chars = len(UZBEK_PATTERN.findall(text))
        if rus_chars > uz_chars:
            return "ru"
        return "uz"
    return "en"


def _build_system_prompt(user_lang: str) -> str:
    prompts = {
        "uz": (
            "Siz NEXURA AI Security Scanner yordamchisisiz. "
            "Kiberxavfsizlik bo'yicha yordam berasiz. "
            "FAQAT O'ZBEK TILIDA javob bering. Hech qachon boshqa tilda javob bermang."
        ),
        "ru": (
            "Вы помощник NEXURA AI Security Scanner. "
            "Помогаете с кибербезопасностью. "
            "ОТВЕЧАЙТЕ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ. Никогда не отвечайте на других языках."
        ),
        "en": (
            "You are NEXURA AI Security Scanner assistant. "
            "You help with cybersecurity. "
            "Answer ONLY in ENGLISH. Never answer in other languages."
        ),
    }
    return prompts.get(user_lang, prompts["en"])


TRANSLATE_PROMPT_TEMPLATE = (
    "Translate the following text to {target_lang}. "
    "Return ONLY the translation, nothing else.\n\n{text}"
)


async def _translate(text: str, target_lang: str, client: httpx.AsyncClient) -> str:
    """Translate text to target language using Ollama."""
    if target_lang == "en":
        return text
    lang_names = {"uz": "Uzbek", "ru": "Russian"}
    target = lang_names.get(target_lang, "Uzbek")
    prompt = TRANSLATE_PROMPT_TEMPLATE.format(target_lang=target, text=text)
    try:
        resp = await client.post(
            f"{config.OLLAMA_BASE_URL.rstrip('/')}/api/chat",
            json={
                "model": config.OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code == 200:
            data = resp.json()
            translated = data.get("message", {}).get("content", "").strip()
            if translated:
                return translated
    except Exception:
        pass
    return text


async def ask_ollama(message: str) -> dict:
    base_url = config.OLLAMA_BASE_URL
    model = config.OLLAMA_MODEL

    if not base_url:
        return {
            "response": "AI integratsiyasi sozlanmagan. "
                        "OLLAMA_BASE_URL ni .env fayliga qo'shing.",
            "error": True,
        }

    user_lang = _detect_lang(message)
    system_prompt = _build_system_prompt(user_lang)

    try:
        async with httpx.AsyncClient(timeout=config.OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                    ],
                    "stream": False,
                },
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            msg = data.get("message", {})
            response_text = msg.get("content", "Javob olinmadi")

            # If user asked in Uzbek/Russian but AI responded in English, translate
            if user_lang != "en":
                detected_response_lang = _detect_lang(response_text)
                if detected_response_lang != user_lang:
                    translated = await _translate(response_text, user_lang, client)
                    if translated != response_text:
                        response_text = translated

            return {
                "response": response_text,
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
