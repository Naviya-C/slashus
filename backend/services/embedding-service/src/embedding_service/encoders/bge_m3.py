"""FastEmbed registration for the official BGE-M3 ONNX export."""

from __future__ import annotations

from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType

BGE_M3_MODEL = "BAAI/bge-m3"


def register_bge_m3() -> None:
    """Register BGE-M3 until it ships in a stable FastEmbed release."""
    supported = {
        description["model"].lower()
        for description in TextEmbedding.list_supported_models()
    }
    if BGE_M3_MODEL.lower() in supported:
        return

    TextEmbedding.add_custom_model(
        model=BGE_M3_MODEL,
        pooling=PoolingType.CLS,
        normalization=True,
        sources=ModelSource(hf=BGE_M3_MODEL),
        dim=1024,
        model_file="onnx/model.onnx",
        additional_files=["onnx/model.onnx_data"],
        description="BGE-M3 multilingual dense embedding model",
        license="mit",
        size_in_gb=2.27,
    )


def register_model(model_name: str) -> None:
    """Register custom models required by this service."""
    if model_name.lower() == BGE_M3_MODEL.lower():
        register_bge_m3()
