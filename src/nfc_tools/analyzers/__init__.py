"""Eager-import built-in analyzers so they self-register."""

# Role: Populates the analyzer registry when the package is imported.
# Dependencies: base defines the registry; birdnet, nighthawk, and wingbeats register
# built-in implementations.
from . import birdnet, nighthawk, wingbeats  # noqa: F401
from .base import get, register, AnalyzerResult  # noqa: F401
