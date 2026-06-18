"""Analyzer plugin protocol.

A plugin is any object with a `name` attribute and a `.run(wav_path,
output_dir, cfg)` method returning an AnalyzerResult. Plugins register
via the registry below. The package currently imports only the built-in
plugins; external plugin discovery should be added here before documenting a
drop-in analyzer directory for users.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class AnalyzerResult:
    name: str
    success: bool
    output_dir: Path
    detections_count: int = 0
    message: str = ""


class Analyzer(Protocol):
    name: str
    def run(self, wav_path: Path, output_dir: Path, cfg) -> AnalyzerResult: ...


_REGISTRY: dict = {}


def register(plugin) -> "Analyzer":
    _REGISTRY[plugin.name] = plugin
    return plugin


def get(name: str):
    if name not in _REGISTRY:
        raise KeyError(f"Unknown analyzer: {name}")
    return _REGISTRY[name]


def all_names() -> list:
    return list(_REGISTRY)
