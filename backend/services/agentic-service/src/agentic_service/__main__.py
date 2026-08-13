"""CLI."""

from __future__ import annotations

import asyncio

import typer

cli = typer.Typer(add_completion=False, help="Slashus agentic tutor")


@cli.command()
def serve() -> None:
    """Run the HTTP API."""
    from agentic_service.runtime import serve as _serve

    asyncio.run(_serve())


@cli.command()
def check() -> None:
    """Validate configuration and dependency reachability."""
    from agentic_service.config.settings import get_settings
    from agentic_service.prompts.pool import get_prompt_pool

    settings = get_settings()
    typer.echo(f"environment : {settings.environment}")
    typer.echo(f"model       : {settings.llm.model} (native tool calling)")
    typer.echo(f"vector      : {settings.vector.grpc_url}")
    typer.echo("memory      : working + semantic + episodic + procedural")
    typer.echo(
        f"cache       : {'on' if settings.cache.enabled else 'off'}, "
        f"threshold={settings.cache.similarity_threshold} "
        f"(greetings always answered live)"
    )
    typer.echo(f"prompts     : {len(get_prompt_pool().names())} templates")
    typer.echo(f"redis       : {'set' if settings.redis.url else 'NOT SET (single replica only)'}")


@cli.command()
def tools() -> None:
    """List the tools the model may choose from."""
    from agentic_service.agent.tools import build_tools

    for t in build_tools(None, None):
        typer.echo(f"- {t.name}: {(t.description or '').splitlines()[0]}")


if __name__ == "__main__":
    cli()
