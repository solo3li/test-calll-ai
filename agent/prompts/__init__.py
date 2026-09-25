"""Prompts package for Voice AI Agent."""
from .dialects import DIALECT_RULES_MAP
from .verbosity import VERBOSITY_INSTRUCTIONS
from .builder import build_dynamic_system_instruction

__all__ = [
    "DIALECT_RULES_MAP",
    "VERBOSITY_INSTRUCTIONS",
    "build_dynamic_system_instruction",
]
