#!/usr/bin/env python
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DifficultyPreset:
    name: str
    rating: int
    lanes: int
    notes_per_30s: int
    min_gap: float
    note_speed: float
    perfect_window: float
    good_window: float
    allow_doubles: bool = False
    allow_holds: bool = False
    description: str = ""

    def max_notes_for_duration(self, duration_seconds: float) -> int:
        return max(1, int(round(self.notes_per_30s * duration_seconds / 30.0)))

    def to_chart_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Keep chart JSON compact/stable and avoid duplicating docs-only text in every note.
        return {
            "name": d["name"],
            "rating": d["rating"],
            "lanes": d["lanes"],
            "notes_per_30s": d["notes_per_30s"],
            "min_gap": d["min_gap"],
            "note_speed": d["note_speed"],
            "perfect_window": d["perfect_window"],
            "good_window": d["good_window"],
            "allow_doubles": d["allow_doubles"],
            "allow_holds": d["allow_holds"],
        }


PRESETS: dict[str, DifficultyPreset] = {
    "easy": DifficultyPreset(
        name="easy",
        rating=2,
        lanes=2,
        notes_per_30s=42,
        min_gap=0.42,
        note_speed=360,
        perfect_window=0.080,
        good_window=0.160,
        allow_doubles=False,
        allow_holds=False,
        description="Beginner-friendly: 2 lanes, sparse notes, generous timing.",
    ),
    "normal": DifficultyPreset(
        name="normal",
        rating=4,
        lanes=4,
        notes_per_30s=75,
        min_gap=0.28,
        note_speed=520,
        perfect_window=0.060,
        good_window=0.120,
        allow_doubles=False,
        allow_holds=False,
        description="Default playable chart: 4 lanes, moderate density.",
    ),
    "hard": DifficultyPreset(
        name="hard",
        rating=7,
        lanes=4,
        notes_per_30s=125,
        min_gap=0.18,
        note_speed=650,
        perfect_window=0.045,
        good_window=0.090,
        allow_doubles=True,
        allow_holds=True,
        description="Challenge chart: higher density and stricter timing.",
    ),
    "expert": DifficultyPreset(
        name="expert",
        rating=9,
        lanes=5,
        notes_per_30s=175,
        min_gap=0.11,
        note_speed=780,
        perfect_window=0.035,
        good_window=0.070,
        allow_doubles=True,
        allow_holds=True,
        description="High-density expert chart for advanced players.",
    ),
}


def list_presets() -> list[str]:
    return list(PRESETS.keys())


def parse_difficulty_names(difficulty: str | None = None, difficulties: str | None = None) -> list[str]:
    if difficulties:
        names = [p.strip().lower() for p in difficulties.split(",") if p.strip()]
    elif difficulty:
        names = [difficulty.strip().lower()]
    else:
        names = ["normal"]
    if not names:
        raise ValueError("No difficulty selected")
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def get_preset(name: str) -> DifficultyPreset:
    key = name.lower().strip()
    if key not in PRESETS:
        raise ValueError(f"Unknown difficulty {name!r}. Available: {', '.join(list_presets())}, custom")
    return PRESETS[key]


def custom_preset(
    *,
    lanes: int = 4,
    note_density: float = 2.0,
    min_gap: float = 0.25,
    note_speed: float = 520.0,
    perfect_window: float = 0.060,
    good_window: float = 0.120,
    rating: int = 5,
    allow_doubles: bool = False,
    allow_holds: bool = False,
) -> DifficultyPreset:
    if lanes < 1 or lanes > 8:
        raise ValueError("custom lanes must be between 1 and 8")
    if note_density <= 0:
        raise ValueError("note_density must be positive notes/second")
    return DifficultyPreset(
        name="custom",
        rating=rating,
        lanes=lanes,
        notes_per_30s=max(1, int(round(note_density * 30.0))),
        min_gap=min_gap,
        note_speed=note_speed,
        perfect_window=perfect_window,
        good_window=good_window,
        allow_doubles=allow_doubles,
        allow_holds=allow_holds,
        description="User-defined difficulty preset.",
    )


def resolve_presets_from_args(args: Any) -> list[DifficultyPreset]:
    names = parse_difficulty_names(getattr(args, "difficulty", None), getattr(args, "difficulties", None))
    presets: list[DifficultyPreset] = []
    for name in names:
        if name == "custom":
            presets.append(
                custom_preset(
                    lanes=getattr(args, "lanes", 4) or 4,
                    note_density=getattr(args, "note_density", 2.0) or 2.0,
                    min_gap=getattr(args, "min_gap", 0.25) or 0.25,
                    note_speed=getattr(args, "note_speed", 520.0) or 520.0,
                    perfect_window=getattr(args, "perfect_window", 0.060) or 0.060,
                    good_window=getattr(args, "good_window", 0.120) or 0.120,
                    rating=getattr(args, "rating", 5) or 5,
                    allow_doubles=bool(getattr(args, "allow_doubles", False)),
                    allow_holds=bool(getattr(args, "allow_holds", False)),
                )
            )
        else:
            presets.append(get_preset(name))
    return presets
