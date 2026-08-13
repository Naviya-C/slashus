"""CLI."""

from __future__ import annotations

import asyncio

import typer

from embedding_service.config.settings import get_settings

cli = typer.Typer(add_completion=False, help="Slashus embedding service")


@cli.command()
def serve() -> None:
    """Run gRPC, health API and the Kafka consumer."""
    from embedding_service.runtime import serve as _serve

    asyncio.run(_serve())


@cli.command("create-collection")
def create_collection(name: str = typer.Option(None)) -> None:
    """Create a Qdrant collection and its payload indexes. Idempotent."""
    from embedding_service.store.qdrant import QdrantStore

    settings = get_settings()
    target = name or settings.qdrant.collection

    async def _run() -> None:
        store = QdrantStore(settings.qdrant, settings.retrieval)
        try:
            created = await store.ensure_collection(target, settings.embedding.dimensions)
        finally:
            await store.close()
        typer.echo(f"{target!r}: {'created' if created else 'already exists, unchanged'}")

    asyncio.run(_run())


@cli.command()
def check() -> None:
    """Validate configuration and dependency reachability."""
    from embedding_service.store.qdrant import QdrantStore

    settings = get_settings()
    typer.echo(f"environment : {settings.environment}")
    typer.echo(f"collection  : {settings.qdrant.collection}")
    typer.echo(
        f"dense       : {settings.embedding.model_name} via ONNX "
        f"(quantized={settings.embedding.quantized}, threads={settings.embedding.onnx_threads})"
    )
    typer.echo(
        f"sparse      : Sinhala-aware hashed, {settings.sparse.num_buckets} buckets, stateless"
    )
    typer.echo("fusion      : server-side Qdrant RRF (single round trip)")

    async def _ping() -> bool:
        store = QdrantStore(settings.qdrant, settings.retrieval)
        try:
            return await store.ping()
        finally:
            await store.close()

    ok = asyncio.run(_ping())
    typer.echo(f"qdrant      : {'reachable' if ok else 'UNREACHABLE'}")
    raise typer.Exit(0 if ok else 1)


if __name__ == "__main__":
    cli()
