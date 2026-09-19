"""Eager-import built-in analyzers so they self-register."""
from . import birdnet, nighthawk, wingbeats  # noqa: F401
from .base import all_names, get, register, AnalyzerResult  # noqa: F401
