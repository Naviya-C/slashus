from .chunker import BlockChunker, estimate_tokens

__all__ = ["BlockChunker", "IngestionService", "JobRepository", "estimate_tokens"]


def __getattr__(name: str):
    if name == "JobRepository":
        from .jobs import JobRepository

        return JobRepository
    if name == "IngestionService":
        from .service import IngestionService

        return IngestionService
    raise AttributeError(name)
