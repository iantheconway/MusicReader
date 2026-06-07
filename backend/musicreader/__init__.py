"""MusicReader: procedural sight-reading exercise generation."""

from .generator import GenerationParams, generate_score
from .model import GenerationConfig

__all__ = ["GenerationConfig", "GenerationParams", "generate_score"]
