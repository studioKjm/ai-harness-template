"""CLI entry point for AI Harness Pro."""

import typer
from pathlib import Path
from rich.console import Console

app = typer.Typer(
    name="harness",
    help="AI Harness Pro — Specification-first development with structural guardrails",
)
console = Console()


@app.command()
def interview(
    topic: str = typer.Argument(..., help="What do you want to build?"),
    project: Path = typer.Option(".", help="Project root directory"),
):
    """Start a Socratic interview to clarify requirements."""
    from harness_pro.interview.engine import InterviewEngine

    engine = InterviewEngine(project_root=project)
    result = engine.start(topic)
    console.print(f"\n[green]Interview saved:[/green] {result.output_path}")
    console.print(f"[yellow]Ambiguity Score:[/yellow] {result.ambiguity:.2f}")
    if result.ambiguity <= 0.2:
        console.print("[green]Ready for seed generation. Run: harness seed[/green]")
    else:
        console.print(f"[red]Ambiguity too high ({result.ambiguity:.2f} > 0.2). Continue interview.[/red]")


@app.command()
def seed(
    project: Path = typer.Option(".", help="Project root directory"),
):
    """Generate immutable seed spec from latest interview."""
    from harness_pro.interview.engine import InterviewEngine

    engine = InterviewEngine(project_root=project)
    interview_data = engine.load_latest()
    if not interview_data:
        console.print("[red]No interview found. Run: harness interview 'topic'[/red]")
        raise typer.Exit(1)

    from harness_pro.ontology.extractor import OntologyExtractor

    extractor = OntologyExtractor()
    seed_path = extractor.generate_seed(interview_data, project)
    console.print(f"[green]Seed generated:[/green] {seed_path}")


@app.command()
def evaluate(
    project: Path = typer.Option(".", help="Project root directory"),
):
    """Run 3-stage evaluation against seed spec."""
    from harness_pro.evaluation.pipeline import EvaluationPipeline

    pipeline = EvaluationPipeline(project_root=project)
    result = pipeline.run()

    if result.passed:
        console.print("[green]VERDICT: PASS[/green]")
    else:
        console.print("[red]VERDICT: FAIL[/red]")
        for issue in result.issues:
            console.print(f"  [red]- {issue}[/red]")


@app.command()
def score(
    project: Path = typer.Option(".", help="Project root directory"),
):
    """Calculate ambiguity score for current interview."""
    from harness_pro.scoring.ambiguity import AmbiguityScorer

    scorer = AmbiguityScorer(project_root=project)
    result = scorer.calculate()
    scorer.display(result)


@app.command()
def drift(
    file_path: str = typer.Argument(..., help="File that was changed"),
    project: Path = typer.Option(".", help="Project root directory"),
):
    """Measure drift from seed spec after a file change."""
    from harness_pro.drift.monitor import DriftMonitor

    monitor = DriftMonitor(project_root=project)
    drift_score = monitor.measure(Path(file_path))
    if drift_score > 0.3:
        console.print(f"[red]HIGH DRIFT: {drift_score:.2f}[/red]")
    elif drift_score > 0.1:
        console.print(f"[yellow]MODERATE DRIFT: {drift_score:.2f}[/yellow]")
    else:
        console.print(f"[green]LOW DRIFT: {drift_score:.2f}[/green]")


@app.command()
def status(
    project: Path = typer.Option(".", help="Project root directory"),
):
    """Show current session status."""
    from harness_pro.persistence.store import EventStore

    store = EventStore(project_root=project)
    session = store.get_current_session()
    if session:
        console.print(f"Session: {session.id}")
        console.print(f"Phase:   {session.phase}")
        console.print(f"Seed:    {session.seed_ref or 'none'}")
        console.print(f"Events:  {session.event_count}")
    else:
        console.print("[dim]No active session[/dim]")


@app.command()
def audit(
    action: str = typer.Option(None, help="Filter by action (gate_run, eval_run, rule_change, etc.)"),
    limit: int = typer.Option(20, help="Number of entries to show"),
    summary: bool = typer.Option(False, "--summary", help="Show summary instead of entries"),
    project: Path = typer.Option(".", help="Project root directory"),
):
    """View audit log of gate runs, evaluations, and rule changes."""
    from harness_pro.persistence.store import EventStore

    store = EventStore(project_root=project)

    if summary:
        data = store.get_audit_summary()
        if not data:
            console.print("[dim]No audit log entries[/dim]")
            return
        from rich.table import Table
        table = Table(title="Audit Summary")
        table.add_column("Action", style="cyan")
        table.add_column("Pass", justify="right", style="green")
        table.add_column("Fail", justify="right", style="red")
        table.add_column("Other", justify="right")
        for act, results in data.items():
            table.add_row(
                act,
                str(results.get("pass", 0)),
                str(results.get("fail", 0)),
                str(sum(v for k, v in results.items() if k not in ("pass", "fail"))),
            )
        console.print(table)
    else:
        entries = store.get_audit_log(action=action, limit=limit)
        if not entries:
            console.print("[dim]No audit log entries[/dim]")
            return
        for entry in entries:
            style = "green" if entry.result == "pass" else "red" if entry.result == "fail" else "yellow"
            console.print(
                f"[dim]{entry.timestamp[:19]}[/dim] "
                f"[{style}]{entry.result:>5}[/{style}] "
                f"[cyan]{entry.action:<15}[/cyan] "
                f"{entry.target} "
                f"[dim]({entry.actor})[/dim]"
            )


@app.command()
def trace(
    trace_id: str = typer.Argument(None, help="Trace ID to inspect (default: latest)"),
    recent: int = typer.Option(0, "--recent", help="Show N recent traces"),
    project: Path = typer.Option(".", help="Project root directory"),
):
    """View agent observability traces."""
    from harness_pro.observability.tracer import AgentTracer

    tracer = AgentTracer(project_root=project)

    if recent > 0:
        traces = tracer.get_recent_traces(limit=recent)
        if not traces:
            console.print("[dim]No traces found[/dim]")
            return
        for t in traces:
            console.print(
                f"[dim]{t['created'][:19]}[/dim] "
                f"[cyan]{t['trace_id']}[/cyan] "
                f"{t['phase'] or '-':<12} "
                f"{t['span_count']} spans "
                f"[dim]{t['total_duration_ms']:.0f}ms[/dim]"
            )
    else:
        if trace_id:
            output = tracer.summary(trace_id)
        else:
            traces = tracer.get_recent_traces(limit=1)
            if not traces:
                console.print("[dim]No traces found[/dim]")
                return
            output = tracer.summary(traces[0]["trace_id"])
        console.print(output)


@app.command("test-scaffold")
def test_scaffold(
    stack: str = typer.Option("typescript", help="Target stack (typescript, python, go, rust, etc.)"),
    project: Path = typer.Option(".", help="Project root directory"),
):
    """Generate test scaffolds from seed spec acceptance criteria."""
    from harness_pro.testing.scaffold import TestScaffoldGenerator

    generator = TestScaffoldGenerator(project_root=project)
    result = generator.generate(stack=stack)

    if not result.test_cases:
        console.print("[yellow]No testable acceptance criteria found in seed spec.[/yellow]")
        raise typer.Exit(1)

    console.print(f"[green]Generated {len(result.test_cases)} test case(s):[/green]")
    for f in result.output_files:
        console.print(f"  {f}")
    if result.skipped:
        console.print(f"[dim]Skipped {len(result.skipped)} manual-only criteria: {', '.join(result.skipped)}[/dim]")


@app.command("mcp-serve")
def mcp_serve(
    transport: str = typer.Option("stdio", help="Transport: stdio or sse"),
    project: Path = typer.Option(".", help="Project root directory"),
):
    """Start MCP server exposing harness gates and tools."""
    try:
        from harness_pro.mcp.server import create_server
    except ImportError:
        console.print("[red]MCP not installed. Run: pip install ai-harness-pro[mcp][/red]")
        raise typer.Exit(1)

    server = create_server(project_root=project)
    console.print(f"[green]Starting MCP server (transport: {transport})...[/green]")
    server.run(transport=transport)


if __name__ == "__main__":
    app()
