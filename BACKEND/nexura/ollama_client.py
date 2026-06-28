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


async def _translate_n8n(text: str, target_lang: str) -> str | None:
    """Translate using n8n webhook."""
    if not config.N8N_TRANSLATE_URL:
        return None
    lang_names = {"uz": "Uzbek", "ru": "Russian", "en": "English"}
    target = lang_names.get(target_lang, "Uzbek")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                config.N8N_TRANSLATE_URL,
                json={"text": text, "target_language": target},
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response") or data.get("translated") or data.get("text")
    except Exception:
        pass
    return None


async def _translate_ollama(text: str, target_lang: str, client: httpx.AsyncClient) -> str:
    """Fallback translation using Ollama itself."""
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
    model = config.OLLAMA_MODEL

    # Build URL list: GPU tunnel (11435) first, then VPS CPU (configured)
    base = config.OLLAMA_BASE_URL.rstrip("/")
    urls = [base]
    # Add tunnel URL as preferred if different from configured
    tunnel_url = base.replace(":11434", ":11435")
    if tunnel_url != base and tunnel_url not in urls:
        urls.insert(0, tunnel_url)

    if not base:
        return {
            "response": "AI integratsiyasi sozlanmagan. "
                        "OLLAMA_BASE_URL ni .env fayliga qo'shing.",
            "error": True,
        }

    user_lang = _detect_lang(message)
    system_prompt = _build_system_prompt(user_lang)

    last_error = None
    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=config.OLLAMA_TIMEOUT) as client:
                resp = await client.post(
                    f"{url}/api/chat",
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
                    translated = await _translate_n8n(response_text, user_lang)
                    if not translated:
                        translated = await _translate_ollama(response_text, user_lang, client)
                    if translated != response_text:
                        response_text = translated

            return {"response": response_text, "error": False}
        except Exception as e:
            last_error = e
            logger.warning("Ollama %s ishlamadi: %s", url, e)

    # All URLs failed — return last error
    if isinstance(last_error, httpx.TimeoutException):
        return {
            "response": "AI javob berishda juda uzoq vaqt oldi "
                        f"({config.OLLAMA_TIMEOUT} soniyadan ortiq). "
                        "Qaytadan urinib ko'ring.",
            "error": True,
        }
    if isinstance(last_error, httpx.HTTPStatusError):
        return {"response": f"Ollama bilan aloqa xatosi: {last_error.response.status_code}", "error": True}
    logger.error("ollama client error: %s", last_error, exc_info=True)
    return {"response": f"Kutilmagan xato: {str(last_error)}", "error": True}
