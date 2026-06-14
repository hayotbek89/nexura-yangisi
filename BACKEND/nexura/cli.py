from datetime import datetime

import click
import uvicorn
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from nexura.ai_engine import get_engine
from nexura.config import MODELS_DIR, TOOL_PATHS, WEB_HOST, WEB_PORT, ensure_dirs, is_tool_available
from nexura.models.schemas import ToolType
from nexura.report.generator import ReportGenerator
from nexura.runner import ScanRunner
from nexura.scanners.network import NetworkScanner
from nexura.tool_selector import ToolSelector
from nexura.web.app import app

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="nexura")
def cli():
    """NEXURA Scanner — AI-powered vulnerability scanner

    Natural language orqali zaifliklarni aniqlang.

    Tez boshlash:  nexura web
    CLI rejimi:    nexura scan "example.com ni tekshir"
    """


@cli.command()
def web():
    """Web UI (tavsiya etiladi) - Brauzerda oching"""
    console.print(f"[green]Web UI: http://{WEB_HOST}:{WEB_PORT}[/]")
    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT, log_level="info")


@cli.command()
@click.argument("prompt", nargs=-1, required=True)
@click.option("--target", "-t", help="Target URL/IP (agar promptda ko'rsatilmagan bo'lsa)")
@click.option("--output", "-o", help="Hisobot fayli (JSON yoki HTML)")
@click.option("--format", "-f", "output_format", type=click.Choice(["json", "html", "both"]), default="both")
@click.option("--deep", is_flag=True, help="Chuqur skanerlash (uzoqroq davom etadi)")
@click.option("--yes", "-y", "skip_confirm", is_flag=True, help="Tasdiqlashni so'ramaslik")
def scan(prompt, target, output, output_format, deep, skip_confirm):
    """Tabiiy til buyrug'i orqali skanerlash

    PROMPT: "bu saytni zaifliklarini aniqlang", "80-portni tekshir", "SQL injection bormi?"
    """
    prompt_text = " ".join(prompt)
    console.print(Panel(f"[bold cyan]{prompt_text}[/]", title="📋 Prompt", border_style="cyan"))

    console.print("[yellow]⏳ AI tahlil qilmoqda...[/]")

    engine = get_engine()
    selector = ToolSelector(engine)

    plan = selector.create_plan(prompt_text, target)
    console.print(
        Panel(
            Markdown(f"**Maqsad:** {plan.intent}\n\n**Reasoning:** {plan.reasoning}"),
            title="🎯 Reja",
            border_style="green",
        )
    )

    for tc in plan.tools:
        console.print(f"  [bold]{'▶'}[/] [cyan]{tc.tool.value}[/] [dim]{tc.description}[/]")

    if not skip_confirm and not click.confirm("\nDavom etamizmi?", default=True):
        console.print("[yellow]Bekor qilindi.[/]")
        return

    runner = ScanRunner()
    reporter = ReportGenerator()
    report = reporter.create_report(plan.target, plan.intent)

    with console.status("[bold green]Skanerlash...[bold]") as status:
        for tc in plan.tools:
            status.update(f"[bold green]▶ {tc.tool.value}: {tc.description}[/]")
            result = runner.run(tc, plan.target)
            report.results.append(result)

    report.end_time = datetime.now()
    report.status = "completed"

    output_path = reporter.save(report, fmt=output_format, path=output)
    runner.close()

    if output_path:
        console.print(f"\n[green]✅ Hisobot: {output_path}[/]")

    console.print(Panel(Markdown(reporter.summary_md(report)), title="📊 Xulosa", border_style="blue"))


@cli.command()
@click.argument("target")
@click.option("--ports", default="22,80,443,8080", help="Tekshiriladigan portlar")
def quick(target, ports):
    """Tezkor port skanerlash (AI talab qilmaydi)"""
    scanner = NetworkScanner()
    with console.status("[bold green]Portlar tekshirilmoqda...[/]") as _:
        result = scanner.quick_scan(target, [int(p) for p in ports.split(",")])

    for port in result.ports:
        icon = "🔓" if port.state == "open" else "🔒"
        console.print(f"  {icon} [bold]{port.port}[/]/{port.service or 'unknown'} ({port.state})")

    console.print(f"\n[green]✅ {len(result.ports)} port tekshirildi[/]")


@cli.command()
def list_models():
    """GGUF modellar ro'yxatini ko'rsatish"""
    ensure_dirs()
    models = list(MODELS_DIR.glob("*.gguf"))
    if not models:
        console.print("[yellow]⚠️ Hech qanday GGUF model topilmadi.[/]")
        console.print(f"Model faylni [bold]{MODELS_DIR}[/] ga joylashtiring.")
        console.print("Tavsiya: Qwen 2.5 7B Instruct (Q4_K_M quantization)")
        return

    for m in models:
        size_gb = m.stat().st_size / (1024**3)
        console.print(f"  [cyan]{m.name}[/] ({size_gb:.2f} GB)")


@cli.command()
def list_tools():
    """Mavjud vositalar ro'yxatini ko'rsatish"""
    descriptions = {
        ToolType.NMAP: "Network port va service skanerlash",
        ToolType.NUCLEI: "Template asosida zaiflik skanerlash (CVE)",
        ToolType.NIKTO: "Web server vulnerability scanner",
        ToolType.SQLMAP: "SQL injection detection va exploitation",
        ToolType.GOBUSTER: "Directory/file brute-forcing, subdomain discovery",
        ToolType.AMASS: "Subdomain enumeration va attack surface mapping",
        ToolType.NETWORK: "Built-in Python socket port skaner (AIsiz)",
    }

    console.print("[bold cyan]Mavjud vositalar[/]")
    console.print("-" * 50)

    for tool in ToolType:
        if tool == ToolType.NETWORK:
            status = "[green]OK[/]"
            note = "[dim](built-in)[/]"
        else:
            available = is_tool_available(tool.value)
            if available:
                path = TOOL_PATHS.get(tool.value, tool.value)
                status = "[green]OK[/]"
                note = f"[dim]({path})[/]"
            else:
                status = "[red]--[/]"
                note = "[red](o'rnatilmagan)[/]"
        console.print(f"  {status}  [bold]{tool.value:12s}[/]  {descriptions[tool]}  {note}")


if __name__ == "__main__":
    cli()
