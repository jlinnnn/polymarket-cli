"""`polymarket serve` — launch the browser demo."""

from typing import Annotated

import typer

from polymarket_cli.display.tables import console


def serve(
    host: Annotated[str, typer.Option("--host", help="Host to bind")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="Port to bind")] = 8000,
    reload: Annotated[bool, typer.Option("--reload", help="Auto-reload on code changes")] = False,
) -> None:
    """Serve the interactive web demo (needs the 'web' extra)."""
    try:
        import uvicorn  # noqa: F401
        import fastapi  # noqa: F401
    except ImportError:
        console.print(
            "[red]The web demo needs extra dependencies.[/red]\n"
            "Install them with: [bold]pip install -e \".[web]\"[/bold]"
        )
        raise typer.Exit(1)

    url = f"http://{host}:{port}"
    console.print(f"[green]Polymarket web demo running at[/green] [bold]{url}[/bold]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")

    uvicorn.run(
        "polymarket_cli.web.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="warning",
    )
