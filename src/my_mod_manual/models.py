from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModSpec:
    modid: str
    display_name: str
    enabled_formats: tuple[str, ...]


@dataclass(frozen=True)
class Manifest:
    version: int
    mods: tuple[ModSpec, ...]
