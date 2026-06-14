from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from nexura import config
from nexura.models.schemas import ScanReport

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


class ReportGenerator:
    def __init__(self):
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True,
        )

    def create_report(self, target: str, intent: str) -> ScanReport:
        return ScanReport(
            id=uuid.uuid4().hex[:12],
            target=target,
            intent=intent,
            start_time=datetime.now(),
        )

    def save(self, report: ScanReport, fmt: str = "both", path: str | None = None) -> str | None:
        config.ensure_dirs()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = report.target.replace("://", "_").replace("/", "_").replace("\\", "_")[:30]
        base = Path(path or str(config.REPORTS_DIR / f"{safe}_{ts}"))

        if fmt in ("json", "both"):
            json_path = base.with_suffix(".json")
            data = report.model_dump(mode="json", exclude_none=True)
            json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

        if fmt in ("html", "both"):
            html_path = base.with_suffix(".html")
            html = self._render_html(report)
            html_path.write_text(html, encoding="utf-8")
            report.html_path = str(html_path)
            return str(html_path)

        return str(json_path) if fmt in ("json", "both") else str(base.with_suffix(".json"))

    def _render_html(self, report: ScanReport) -> str:
        total_vulns = sum(len(r.vulnerabilities) for r in report.results)
        total_ports = sum(len(r.ports) for r in report.results)
        vulns_by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for r in report.results:
            for v in r.vulnerabilities:
                sev = v.severity.upper()
                if sev in vulns_by_severity:
                    vulns_by_severity[sev] += 1

        technologies = report.technologies

        template = self._env.get_template("report.html")
        return template.render(
            report=report,
            total_vulns=total_vulns,
            total_ports=total_ports,
            vulns_by_severity=vulns_by_severity,
            technologies=technologies,
        )

    def summary_md(self, report: ScanReport) -> str:
        lines = []
        lines.append(f"**Target:** {report.target}")
        lines.append(f"**Intent:** {report.intent}")
        lines.append(f"**Duration:** {_fmt_duration(report.start_time, report.end_time)}")
        lines.append("")
        for r in report.results:
            icon = "✅" if r.success else "❌"
            lines.append(f"{icon} **{r.tool.upper()}**: {r.summary or 'Done'}")
            if r.ports:
                for p in r.ports:
                    lines.append(f"  - 🔓 Port {p.port}/{p.service}")
            if r.vulnerabilities:
              for v in r.vulnerabilities[:10]:
                  lines.append(f"  - ⚠️ {v.name} [{v.severity}]")
              if len(r.vulnerabilities) > 10:
                  lines.append(f"  - ... va yana {len(r.vulnerabilities) - 10} ta")
        return "\n".join(lines)


def _fmt_duration(start: datetime, end: datetime | None) -> str:
    if not end:
        return "N/A"
    delta = end - start
    total = int(delta.total_seconds())
    m, s = divmod(total, 60)
    return f"{m}m {s}s"
