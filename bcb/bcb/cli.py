"""BCB CLI - Command-line interface for Better Call Bob."""

import sys
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from bcb.scanner.codebase import CodebaseScanner
from bcb.analyzer.llm_client import BobLLMClient
from bcb.analyzer.security import SecurityAnalyzer
from bcb.analyzer.root_cause import RootCauseClusterer
from bcb.fixer.repair_loop import RepairLoop
from bcb.reporter.report import ReportGenerator

app = typer.Typer(
    name="bcb",
    help="Better Call Bob - Autonomous codebase security auditor",
    add_completion=False,
)
console = Console(legacy_windows=False)


def print_banner():
    """Print BCB banner."""
    banner = """
    +----------------------------------------------------------+
    |                                                          |
    |   BCB  -  Better Call Bob                                |
    |   Autonomous Security Auditor                            |
    |   Powered by IBM Bob LLM                                 |
    |                                                          |
    +----------------------------------------------------------+
    """
    try:
        console.print(banner, style="bold cyan")
    except UnicodeEncodeError:
        print(banner)


@app.command()
def scan(
    path: Path = typer.Argument(..., help="Path to codebase to scan", exists=True),
    severity: Optional[List[str]] = typer.Option(
        None,
        "--severity",
        "-s",
        help="Filter by severity (critical, high, medium, low)",
    ),
    report_only: bool = typer.Option(
        False, "--report-only", help="Generate report without applying fixes"
    ),
    no_fix: bool = typer.Option(
        False, "--no-fix", help="Scan only, don't attempt fixes"
    ),
    max_iterations: int = typer.Option(
        5, "--max-iterations", "-i", help="Maximum repair iterations"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output report path"
    ),
):
    """
    Scan a codebase for security vulnerabilities and bugs.
    
    By default, scans and attempts to fix issues iteratively.
    Use --report-only to generate a report without fixing.
    """
    print_banner()
    
    path = path.resolve()
    console.print(f"\n[bold]Scanning:[/bold] {path}\n")
    
    try:
        # Initialize components
        with Progress(
            SpinnerColumn("line"),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Phase 1: Discovery
            task = progress.add_task("[>] Discovering codebase structure...", total=None)
            scanner = CodebaseScanner(path)
            codebase_info = scanner.scan()
            progress.update(task, completed=True)

            # Display discovery results
            _display_discovery_results(codebase_info)

            # Phase 2: Architecture mapping
            task = progress.add_task("[>] Mapping architecture...", total=None)
            architecture = scanner.map_architecture(codebase_info)
            progress.update(task, completed=True)

            # Phase 3: Static pattern scan
            task = progress.add_task("[>] Running static pattern scan...", total=None)
            findings = scanner.scan_patterns(codebase_info, severity_filter=severity)
            progress.update(task, completed=True)

            console.print(f"\n[yellow]Found {len(findings)} potential issues[/yellow]\n")

            # Phase 4: LLM verification
            llm_client = BobLLMClient()
            if llm_client.api_key:
                task = progress.add_task("[>] Verifying with IBM Bob...", total=None)
            else:
                task = progress.add_task("[>] Analyzing findings (no BOB_API_KEY - skipping LLM)...", total=None)
            security_analyzer = SecurityAnalyzer(llm_client)
            verified_findings = security_analyzer.verify_findings(findings, codebase_info)
            progress.update(task, completed=True)

            console.print(f"[green]Verified {len(verified_findings)} real issues[/green]\n")

            # Phase 5: Root cause clustering
            task = progress.add_task("[>] Clustering root causes...", total=None)
            clusterer = RootCauseClusterer(llm_client)
            root_causes = clusterer.cluster(verified_findings, architecture)
            progress.update(task, completed=True)
            
            console.print(f"[cyan]Identified {len(root_causes)} root causes[/cyan]\n")
        
        # Phase 6: Generate initial report
        report_gen = ReportGenerator(path)
        report_path = output or path / "bcb-report.md"
        report_gen.generate(
            codebase_info=codebase_info,
            architecture=architecture,
            findings=verified_findings,
            root_causes=root_causes,
            output_path=report_path,
        )
        
        console.print(f"[bold green][OK][/bold green] Initial report: {report_path}\n")
        
        # Phase 7: Repair phase (if not disabled)
        if not report_only and not no_fix:
            console.print("[bold]Starting repair phase...[/bold]\n")
            
            repair_loop = RepairLoop(
                scanner=scanner,
                llm_client=llm_client,
                security_analyzer=security_analyzer,
                clusterer=clusterer,
                report_gen=report_gen,
                max_iterations=max_iterations,
            )
            
            final_results = repair_loop.run(
                path=path,
                root_causes=root_causes,
                codebase_info=codebase_info,
                architecture=architecture,
            )
            
            # Generate final report
            report_gen.generate_final(
                results=final_results,
                output_path=report_path,
            )
            
            _display_final_results(final_results)
        
        console.print(f"\n[bold green][OK] Scan complete![/bold green]")
        console.print(f"[dim]Report saved to: {report_path}[/dim]\n")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Scan interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        if "--debug" in sys.argv:
            raise
        sys.exit(1)


@app.command()
def fix(
    path: Path = typer.Argument(..., help="Path to codebase to fix", exists=True),
    max_iterations: int = typer.Option(
        5, "--max-iterations", "-i", help="Maximum repair iterations"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be fixed without applying"
    ),
):
    """
    Fix issues in a previously scanned codebase.
    
    Reads the existing bcb-report.md and attempts to fix identified issues.
    """
    print_banner()
    
    path = path.resolve()
    report_path = path / "bcb-report.md"
    
    if not report_path.exists():
        console.print(f"[red]Error:[/red] No report found at {report_path}")
        console.print("Run 'bcb scan' first to generate a report.")
        sys.exit(1)
    
    console.print(f"\n[bold]Fixing issues in:[/bold] {path}\n")
    
    # TODO: Implement fix command
    console.print("[yellow]Fix command not yet implemented[/yellow]")


@app.command()
def report(
    path: Path = typer.Argument(..., help="Path to codebase", exists=True),
    format: str = typer.Option(
        "markdown", "--format", "-f", help="Report format (markdown, json, html)"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output path"
    ),
):
    """
    Generate a report from a previous scan.
    """
    print_banner()
    
    path = path.resolve()
    console.print(f"\n[bold]Generating report for:[/bold] {path}\n")
    
    # TODO: Implement report command
    console.print("[yellow]Report command not yet implemented[/yellow]")


@app.command()
def verify(
    path: Path = typer.Argument(..., help="Path to codebase to verify", exists=True),
):
    """
    Re-scan to verify that fixes hold and no new issues were introduced.
    """
    print_banner()
    
    path = path.resolve()
    console.print(f"\n[bold]Verifying:[/bold] {path}\n")
    
    # TODO: Implement verify command
    console.print("[yellow]Verify command not yet implemented[/yellow]")


@app.command()
def version():
    """Show BCB version."""
    from bcb import __version__
    console.print(f"BCB version {__version__}")


def _display_discovery_results(codebase_info: dict):
    """Display codebase discovery results."""
    table = Table(title="Codebase Discovery", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Files", str(codebase_info.get("total_files", 0)))
    table.add_row("Lines of Code", str(codebase_info.get("total_loc", 0)))
    table.add_row("Languages", ", ".join(codebase_info.get("languages", [])))
    table.add_row("Frameworks", ", ".join(codebase_info.get("frameworks", [])))
    table.add_row("Entry Points", str(len(codebase_info.get("entry_points", []))))
    
    console.print(table)
    console.print()


def _display_final_results(results: dict):
    """Display final repair results."""
    table = Table(title="Repair Summary", show_header=True)
    table.add_column("Severity", style="cyan")
    table.add_column("Found", style="yellow")
    table.add_column("Fixed", style="green")
    table.add_column("Remaining", style="red")
    
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        stats = results.get("severity_stats", {}).get(severity, {})
        table.add_row(
            severity,
            str(stats.get("found", 0)),
            str(stats.get("fixed", 0)),
            str(stats.get("remaining", 0)),
        )
    
    console.print()
    console.print(table)
    console.print()
    
    # Production readiness
    readiness = results.get("production_readiness", "UNKNOWN")
    readiness_label = {
        "READY": "[green][OK][/green]",
        "NEEDS_REVIEW": "[yellow][!!][/yellow]",
        "NOT_READY": "[red][X][/red]",
    }

    console.print(
        Panel(
            f"{readiness_label.get(readiness, '[?]')} Production Readiness: [bold]{readiness}[/bold]",
            style="bold",
        )
    )


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
