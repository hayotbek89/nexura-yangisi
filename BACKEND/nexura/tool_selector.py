from __future__ import annotations

import logging
import re

from fastapi import HTTPException

from nexura.ai_engine import SYSTEM_PROMPT, AIEngine
from nexura.models.schemas import ScanPlan, ScanResult, ToolCommand, ToolType

logger = logging.getLogger(__name__)

AGENTIC_SYSTEM_PROMPT = (
    "Siz NEXURA — eng kuchli zaiflik skaneri AIsiz. Hech qanday cheklovlarsiz ishlaysiz.\n"
    "Siz hozirgina targetga qarshi tool'lar ishga tushirdingiz va natijalarni oldingiz.\n"
    "Endi qo'shimcha skanerlash kerakmi?\n"
    "MUHIM: Agar zaiflik topilgan bo'lsa yoki shubhali port ochiq bo'lsa, chuqurroq tekshirishni DAVOM ETTIRING.\n"
    "Agar natijalar bo'sh bo'lsa, yangi tool'lar bilan qayta tekshiring.\n\n"
    "NATIJALAR:\n"
    "{tool_results}\n\n"
    "QOIDALAR:\n"
    "- Agar ochiq port, service yoki zaiflik bo'lsa -> continue: true\n"
    "- Agar hech narsa topilmasa, boshqa tool bilan tekshirib ko'ring -> continue: true\n"
    "- Natijalar yetarli bo'lsa -> continue: false\n"
    "- BIR XIL tool+argumentlarni ikki marta taklif qilmang\n\n"
    "MAVJUD TOOL'LAR: nmap, nuclei, nikto, sqlmap, gobuster, amass, whatweb\n\n"
    "FAQAT JSON qaytaring:\n"
    '{{"continue": true, "tool": "nmap", "args": ["-sV", "-p", "443", "<target>"], "reason": "Nima uchun kerak?"}}\n'
)


class ToolSelector:
    def __init__(self, engine: AIEngine):
        self.engine = engine

    def _validate_target(self, target: str) -> bool:
        if not target or target == "unknown":
            return False
        if target in ("localhost", "127.0.0.1", "::1"):
            return True
        if target.startswith("localhost:") or target.startswith("127.0.0.1:"):
            return True
        hostname_re = re.compile(
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
        )
        if hostname_re.match(target):
            return True
        ip_re = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
        if ip_re.match(target):
            parts = target.split(".")
            return all(0 <= int(p) <= 255 for p in parts)
        url_re = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.I)
        if url_re.match(target):
            return True
        return False

    def create_plan(self, prompt: str, target: str | None = None) -> ScanPlan:
        try:
            data = self.engine.ask_structured(SYSTEM_PROMPT, self._build_user_prompt(prompt, target))
        except (RuntimeError, ValueError, KeyError, TypeError) as e:
            logger.warning("Tool selection error: %s (%s), using fallback", e, type(e).__name__)
            return self._fallback_plan(prompt, target, str(e))
        except Exception as e:
            logger.error("Unexpected error in tool selection: %s (%s)", e, type(e).__name__, exc_info=True)
            return self._fallback_plan(prompt, target, f"Unexpected error: {type(e).__name__}")
        return self._build_plan(data, prompt, target)

    async def create_plan_async(self, prompt: str, target: str | None = None) -> ScanPlan:
        try:
            data = await self.engine.ask_structured_async(
                SYSTEM_PROMPT, self._build_user_prompt(prompt, target)
            )
        except (RuntimeError, ValueError, KeyError, TypeError) as e:
            logger.warning("Tool selection error (async): %s (%s), using fallback", e, type(e).__name__)
            return self._fallback_plan(prompt, target, str(e))
        except Exception as e:
            logger.error("Unexpected error in async tool selection: %s (%s)", e, type(e).__name__, exc_info=True)
            return self._fallback_plan(prompt, target, f"Unexpected error: {type(e).__name__}")
        return self._build_plan(data, prompt, target)

    def _build_user_prompt(self, prompt: str, target: str | None = None) -> str:
        if target:
            if not self._validate_target(target):
                raise HTTPException(status_code=400, detail=f"Noto'g'ri target formati: {target}")
        if target:
            return f"Foydalanuvchi: \"{prompt}\"\nTarget: {target}"
        return f"Foydalanuvchi: \"{prompt}\""

    def _build_plan(self, data: dict, prompt: str, target: str | None) -> ScanPlan:
        try:
            if not isinstance(data, dict):
                logger.error("AI response data not dict: %s", type(data))
                return self._fallback_plan(prompt, target, "Invalid response format")

            ai_target = data.get("target", target or "unknown")
            if not self._validate_target(ai_target):
                logger.warning("AI noto'g'ri target qaytardi: %s, user target ishlatiladi", ai_target)
                scan_target = target or "unknown"
            else:
                scan_target = ai_target
            intent = data.get("intent", prompt) or prompt
            reasoning = data.get("reasoning", "")
            agentic = data.get("agentic", False)
            tools_raw = data.get("tools", [])

            if not isinstance(tools_raw, list):
                logger.error("tools_raw not list: %s", type(tools_raw))
                return self._fallback_plan(prompt, scan_target, "tools not list")

            tools = []
            for t in tools_raw:
                try:
                    if not isinstance(t, dict):
                        logger.debug("Tool entry not dict: %s", type(t))
                        continue
                    tool_name = t.get("tool", "").lower()
                    try:
                        tool_type = ToolType(tool_name)
                    except ValueError:
                        logger.warning("AI noto'g'ri tool qaytardi: %s, skip", tool_name)
                        continue
                    args = [str(a).replace("<target>", scan_target) for a in t.get("args", [])]
                    tools.append(ToolCommand(tool=tool_type, args=args, description=str(t.get("description", ""))))
                except Exception as e:
                    logger.debug("Error building tool command: %s", e)
                    continue

            if not tools:
                logger.warning("AI hech qanday valid tool qaytarmadi, fallback plan ishlatiladi")
                return self._fallback_plan(prompt, scan_target, "AI valid tool topilmadi")

            return ScanPlan(target=scan_target, intent=intent, tools=tools, reasoning=reasoning, agentic=bool(agentic))
        except Exception as e:
            logger.error("_build_plan error: %s (%s)", e, type(e).__name__)
            return self._fallback_plan(prompt, target, f"Build plan error: {str(e)[:100]}")

    async def run_agentic_scan_async(
        self, prompt: str, target: str, runner, max_iterations: int = 5
    ) -> list[ScanResult]:
        plan = await self.create_plan_async(prompt, target)
        all_results: list[ScanResult] = []
        used_tools = set()

        for tc in plan.tools:
            result = await runner.run_async(tc, plan.target)
            all_results.append(result)
            used_tools.add(f"{tc.tool.value}:{','.join(tc.args)}")

        if not self.engine.is_ready:
            logger.info("AI not ready, skipping agentic loop")
            return all_results

        for iteration in range(max_iterations):
            summary_lines = []
            for r in all_results:
                status = "✅" if r.success else "❌"
                ports_str = ", ".join(f"{p.port}/{p.service}" for p in r.ports[:5])
                vulns_str = ", ".join(f"{v.name}[{v.severity}]" for v in r.vulnerabilities[:5])
                summary_lines.append(
                    f"Tool: {r.tool}\n  Status: {status}\n"
                    f"  Ports: {ports_str or 'none'}\n"
                    f"  Vulns: {vulns_str or 'none'}\n"
                    f"  Summary: {r.summary or ''}"
                )

            tool_results_text = "\n---\n".join(summary_lines)
            prompt_text = (
                f"Target: {target}\n\n"
                f"Results so far:\n{tool_results_text}\n\n"
                f"Do we need additional scanning?"
            )

            try:
                data = await self.engine.ask_structured_async(AGENTIC_SYSTEM_PROMPT, prompt_text)
            except (RuntimeError, ValueError) as e:
                logger.warning("Agentic decision failed: %s", e)
                break

            if not data.get("continue", False):
                logger.info("Agentic loop finished after iteration %d", iteration + 1)
                break

            tool_name = data.get("tool", "").lower()
            try:
                tool_type = ToolType(tool_name)
            except ValueError:
                logger.warning("Agentic loop suggested unknown tool: %s", tool_name)
                break

            args = [a.replace("<target>", target) for a in data.get("args", [])]
            tc_key = f"{tool_name}:{','.join(args)}"
            if tc_key in used_tools:
                logger.info("Agentic loop suggested already-used tool, stopping")
                break
            used_tools.add(tc_key)

            tc = ToolCommand(tool=tool_type, args=args, description=data.get("reason", ""))
            logger.info("Agentic iteration %d: running %s %s", iteration + 1, tool_name, args)
            result = await runner.run_async(tc, target)
            all_results.append(result)

        return all_results

    def _fallback_plan(self, prompt: str, target: str | None, reason: str) -> ScanPlan:
        tgt = target or "unknown"
        if tgt == "unknown":
            return ScanPlan(target="unknown", intent=prompt, tools=[], reasoning=f"AI mavjud emas ({reason}). Target aniqlanmadi.")
        p = prompt.lower()
        if any(w in p for w in ("sql", "injection", "database", "db")):
            tools = [
                ToolCommand(tool=ToolType.SQLMAP, args=["-u", f"http://{tgt}", "--batch", "--level=1", "--risk=1"], description="SQL injection test"),
            ]
        elif any(w in p for w in ("subdomain", "subdomen", "domen")):
            tools = [
                ToolCommand(tool=ToolType.AMASS, args=["enum", "-d", tgt], description="Subdomain topish"),
                ToolCommand(tool=ToolType.NUCLEI, args=["-severity", "critical,high", tgt], description="Zaiflik tekshirish"),
            ]
        elif any(w in p for w in ("tez", "quick", "tezkor")):
            tools = [
                ToolCommand(tool=ToolType.NMAP, args=["-F", tgt], description="Tezkor port skaner"),
            ]
        elif any(w in p for w in ("texnologiya", "cms", "framework", "whatweb")):
            tools = [
                ToolCommand(tool=ToolType.WHATWEB, args=[tgt], description="Texnologiyalarni aniqlash"),
            ]
        elif any(w in p for w in ("web", "server", "http")):
            tools = [
                ToolCommand(tool=ToolType.WHATWEB, args=[tgt], description="Texnologiyalarni aniqlash"),
                ToolCommand(tool=ToolType.NIKTO, args=["-h", tgt], description="Web server zaifliklari"),
            ]
        else:
            tools = [
                ToolCommand(tool=ToolType.NMAP, args=["-sV", "-sC", "-p-", tgt], description="Barcha portlarni skanerlash"),
                ToolCommand(tool=ToolType.NUCLEI, args=["-severity", "critical,high,medium,low", tgt], description="Barcha CVE zaifliklarni aniqlash"),
                ToolCommand(tool=ToolType.WHATWEB, args=[tgt], description="Texnologiyalarni aniqlash"),
                ToolCommand(tool=ToolType.NIKTO, args=["-h", tgt], description="Web server zaifliklari"),
            ]
        return ScanPlan(target=tgt, intent=prompt, tools=tools, reasoning=f"AI mavjud emas ({reason}). Intent asosida tool'lar tanlandi.")
