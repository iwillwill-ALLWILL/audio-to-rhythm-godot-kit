#!/usr/bin/env python
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

DEFAULT_LANES = 3


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
    dynamic_density: float = 0.45
    section_seconds: float = 4.0
    double_rate: float = 0.0
    hold_rate: float = 0.0
    hold_min: float = 0.35
    hold_max: float = 0.9
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
            "dynamic_density": d["dynamic_density"],
            "section_seconds": d["section_seconds"],
            "double_rate": d["double_rate"],
            "hold_rate": d["hold_rate"],
            "hold_min": d["hold_min"],
            "hold_max": d["hold_max"],
        }


PRESETS: dict[str, DifficultyPreset] = {
    "easy": DifficultyPreset(
        name="easy",
        rating=2,
        lanes=3,
        notes_per_30s=42,
        min_gap=0.42,
        note_speed=360,
        perfect_window=0.080,
        good_window=0.160,
        allow_doubles=False,
        allow_holds=False,
        dynamic_density=0.25,
        double_rate=0.0,
        hold_rate=0.0,
        description="Beginner-friendly: 3-key A/S/D layout, sparse notes, generous timing.",
    ),
    "normal": DifficultyPreset(
        name="normal",
        rating=4,
        lanes=3,
        notes_per_30s=75,
        min_gap=0.28,
        note_speed=520,
        perfect_window=0.060,
        good_window=0.120,
        allow_doubles=True,
        allow_holds=True,
        dynamic_density=0.45,
        double_rate=0.04,
        hold_rate=0.08,
        hold_min=0.35,
        hold_max=0.75,
        description="Default playable chart: 3-key A/S/D layout, moderate density.",
    ),
    "hard": DifficultyPreset(
        name="hard",
        rating=7,
        lanes=3,
        notes_per_30s=125,
        min_gap=0.18,
        note_speed=650,
        perfect_window=0.045,
        good_window=0.090,
        allow_doubles=True,
        allow_holds=True,
        dynamic_density=0.70,
        double_rate=0.16,
        hold_rate=0.16,
        hold_min=0.35,
        hold_max=1.05,
        description="Challenge chart: 3-key A/S/D layout, higher density and stricter timing.",
    ),
    "expert": DifficultyPreset(
        name="expert",
        rating=9,
        lanes=3,
        notes_per_30s=175,
        min_gap=0.11,
        note_speed=780,
        perfect_window=0.035,
        good_window=0.070,
        allow_doubles=True,
        allow_holds=True,
        dynamic_density=0.90,
        double_rate=0.26,
        hold_rate=0.22,
        hold_min=0.30,
        hold_max=1.20,
        description="High-density expert chart on the same 3-key A/S/D layout.",
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


def with_lane_count(preset: DifficultyPreset, lanes: int) -> DifficultyPreset:
    if lanes != DEFAULT_LANES:
        raise ValueError("This kit is fixed to 3 lanes for the A/S/D product layout")
    if preset.lanes == lanes:
        return preset
    return replace(preset, lanes=lanes)


def custom_preset(
    *,
    lanes: int = 3,
    note_density: float = 2.0,
    min_gap: float = 0.25,
    note_speed: float = 520.0,
    perfect_window: float = 0.060,
    good_window: float = 0.120,
    rating: int = 5,
    allow_doubles: bool = False,
    allow_holds: bool = False,
    dynamic_density: float = 0.55,
    section_seconds: float = 4.0,
    double_rate: float = 0.08,
    hold_rate: float = 0.10,
    hold_min: float = 0.35,
    hold_max: float = 0.9,
) -> DifficultyPreset:
    if lanes != DEFAULT_LANES:
        raise ValueError("custom lanes must be 3 for the A/S/D product layout")
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
        dynamic_density=dynamic_density,
        section_seconds=section_seconds,
        double_rate=double_rate,
        hold_rate=hold_rate,
        hold_min=hold_min,
        hold_max=hold_max,
        description="User-defined difficulty preset.",
    )


def resolve_presets_from_args(args: Any) -> list[DifficultyPreset]:
    names = parse_difficulty_names(getattr(args, "difficulty", None), getattr(args, "difficulties", None))
    presets: list[DifficultyPreset] = []
    for name in names:
        if name == "custom":
            presets.append(
                custom_preset(
                    lanes=getattr(args, "lanes", 3) or 3,
                    note_density=getattr(args, "note_density", 2.0) or 2.0,
                    min_gap=getattr(args, "min_gap", 0.25) or 0.25,
                    note_speed=getattr(args, "note_speed", 520.0) or 520.0,
                    perfect_window=getattr(args, "perfect_window", 0.060) or 0.060,
                    good_window=getattr(args, "good_window", 0.120) or 0.120,
                    rating=getattr(args, "rating", 5) or 5,
                    allow_doubles=bool(getattr(args, "allow_doubles", False)),
                    allow_holds=bool(getattr(args, "allow_holds", False)),
                    dynamic_density=getattr(args, "dynamic_density", 0.55) if getattr(args, "dynamic_density", None) is not None else 0.55,
                    section_seconds=getattr(args, "section_seconds", 4.0) or 4.0,
                    double_rate=getattr(args, "double_rate", 0.08) if getattr(args, "double_rate", None) is not None else 0.08,
                    hold_rate=getattr(args, "hold_rate", 0.10) if getattr(args, "hold_rate", None) is not None else 0.10,
                    hold_min=getattr(args, "hold_min", 0.35) or 0.35,
                    hold_max=getattr(args, "hold_max", 0.9) or 0.9,
                )
            )
        else:
            presets.append(get_preset(name))
    return presets
