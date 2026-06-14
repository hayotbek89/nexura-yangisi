import json
import re
import logging
from nexura.models.schemas import ParserResult, Vulnerability

logger = logging.getLogger(__name__)

def parse_whatweb(raw: str) -> ParserResult:
    if not raw or not isinstance(raw, str):
        logger.warning("whatweb output is empty or invalid")
        return ParserResult(summary="whatweb: No output")

    # Try to find JSON first
    try:
        # Sometimes whatweb outputs multiple lines, some might be JSON
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("[") or line.startswith("{"):
                try:
                    data = json.loads(line)
                    return _parse_json(data)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.debug("whatweb JSON parse line failed: %s", e)
                    continue
    except Exception as e:
        logger.debug("whatweb JSON parsing error: %s", e)

    # Regex fallback for standard output
    # Example: http://example.com [200 OK] Apache[2.4.41], Country[RESERVED][ZZ]...
    try:
        summary = raw.strip().splitlines()[0] if raw.strip() else "No output"
        return ParserResult(summary=f"WhatWeb: {summary[:200]}")
    except Exception as e:
        logger.warning("whatweb fallback parsing failed: %s", e)
        return ParserResult(summary="WhatWeb: Parse error")

def _parse_json(data) -> ParserResult:
    try:
        if isinstance(data, list):
            data = data[0] if data else {}

        if not isinstance(data, dict):
            logger.debug("whatweb data not dict: %s", type(data))
            return ParserResult(summary="WhatWeb: Invalid data format")

        plugins = data.get("plugins", {})
        summary_parts = []
        for name, details in plugins.items():
            try:
                version = ""
                if isinstance(details, dict) and details.get("version"):
                    v = details.get("version")
                    version = f" ({v[0]})" if isinstance(v, list) else f" ({v})"
                summary_parts.append(f"{name}{version}")
            except Exception as e:
                logger.debug("Error parsing whatweb plugin: %s", e)
                continue

        return ParserResult(summary=", ".join(summary_parts) if summary_parts else "No plugins detected")
    except Exception as e:
        logger.warning("whatweb JSON parsing failed: %s", e)
        return ParserResult(summary="WhatWeb: JSON parse error")
