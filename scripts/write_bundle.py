#!/usr/bin/env python
from __future__ import annotations

import json
import re
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

import numpy as np

from analyze_audio import DEFAULT_KEYS, decode_pcm_wav, find_ffmpeg, find_ffmpeg_optional, generate_chart
from difficulty_presets import DifficultyPreset

GENERATOR_NAME = "audio-to-rhythm-godot-kit"
GENERATOR_VERSION = "0.3.0"
BUNDLE_SCHEMA = "com.rhythmkit.bundle.v1"
CHART_SCHEMA = "com.rhythmkit.chart.v1"


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "song"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def find_ffprobe() -> str | None:
    exe = shutil.which("ffprobe")
    if exe:
        return exe
    ffmpeg = find_ffmpeg_optional()
    if not ffmpeg:
        return None
    ffmpeg_path = Path(ffmpeg)
    candidate = ffmpeg_path.with_name("ffprobe.exe")
    if candidate.exists():
        return str(candidate)
    candidate = ffmpeg_path.with_name("ffprobe")
    if candidate.exists():
        return str(candidate)
    return None


def probe_duration(audio_path: Path) -> float | None:
    ffprobe = find_ffprobe()
    if not ffprobe:
        return None
    cmd = [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(audio_path)]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode != 0:
        return None
    try:
        return float(p.stdout.decode("utf-8", "ignore").strip())
    except Exception:
        return None


def convert_audio_for_bundle(src: Path, dst: Path) -> None:
    """Convert arbitrary uploaded audio to a broadly engine-friendly PCM WAV."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg_optional()
    if ffmpeg is None:
        if src.suffix.lower() != ".wav":
            raise RuntimeError("ffmpeg not found on PATH. Non-WAV uploads require ffmpeg or FFMPEG/FFMPEG_PATH.")
        audio, sr = decode_pcm_wav(src, sr=44100)
        pcm = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
        stereo = np.repeat(pcm[:, None], 2, axis=1)
        with wave.open(str(dst), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(stereo.tobytes())
        return
    cmd = [ffmpeg, "-y", "-v", "error", "-i", str(src), "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(dst)]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg audio conversion failed: " + p.stderr.decode("utf-8", "ignore"))


def normalize_chart_for_bundle(
    raw_chart: dict[str, Any],
    *,
    song_id: str,
    title: str,
    artist: str | None,
    preset: DifficultyPreset,
) -> dict[str, Any]:
    lanes = []
    for lane in raw_chart.get("lanes", []):
        lanes.append(
            {
                "id": int(lane.get("id", len(lanes))),
                "name": str(lane.get("name", f"LANE {len(lanes) + 1}")),
                "default_key": str(lane.get("key", lane.get("default_key", ""))),
            }
        )

    notes = []
    lane_count = max(1, len(lanes))
    for idx, note in enumerate(raw_chart.get("notes", []), start=1):
        lane = int(note.get("lane", 0))
        if lane < 0 or lane >= lane_count:
            lane = lane % lane_count
        n = {
            "id": idx,
            "time": float(note.get("time", 0.0)),
            "lane": lane,
            "type": str(note.get("type", "tap")),
            "source": str(note.get("source", "onset")),
            "confidence": float(note.get("confidence", 0.0)),
        }
        if "duration" in note:
            n["duration"] = float(note["duration"])
        if note.get("pitch") is not None:
            n["pitch"] = note.get("pitch")
        if "centroid_hz" in note:
            n["centroid_hz"] = note.get("centroid_hz")
        notes.append(n)

    chart = {
        "schema": CHART_SCHEMA,
        "generator_version": GENERATOR_VERSION,
        "song_id": song_id,
        "title": title,
        "artist": artist or "",
        "audio": "../audio/song.wav",
        "duration": raw_chart.get("duration", 0.0),
        "bpm": raw_chart.get("bpm", 120.0),
        "offset": raw_chart.get("offset", 0.0),
        "theme": raw_chart.get("theme", "generic"),
        "difficulty": preset.to_chart_dict(),
        "lanes": lanes,
        "notes": notes,
    }
    return chart


def integration_readme(song_id: str, difficulties: list[str]) -> str:
    diffs = ", ".join(difficulties)
    return f"""# Rhythm Bundle Integration

This folder is a portable rhythm-game level bundle generated by `{GENERATOR_NAME}`.

It is meant to be imported into the user's own game. The recommended workflow is **AI-first**: give this bundle and the prompt below to Codex / Claude Code / Cursor / Hermes, then let the AI inspect the Godot project, copy files, wire the menu/trigger, and run Godot verification.

## Files

```text
metadata.json              # bundle entry point
audio/song.wav             # engine-friendly PCM WAV audio
charts/*.chart.json        # one chart per difficulty
analysis/report.json       # generation report/debug info
integration/README.md
integration/AI_GODOT_IMPORT_PROMPT.md
```

Available difficulties: `{diffs}`

Current fixed layout:

```text
lane 0 -> A
lane 1 -> S
lane 2 -> D
```

## First-time import into a Godot game

Ask an AI coding agent to do the project work. Human users should not need to hand-write GDScript.

Give the AI:

```text
1. The Godot project path.
2. This bundle folder.
3. Where the rhythm level should appear: main menu / level select / NPC / map trigger / debug entry.
```

Tell the AI to:

```text
1. Inspect the existing Godot project structure first.
2. Add or reuse res://addons/rhythmkit/ as the reusable runtime.
3. Copy this bundle to res://levels/{song_id}/.
4. Connect a menu/scene/trigger to load_bundle("res://levels/{song_id}", "normal").
5. Write docs/rhythm_bundle_import.md inside the user's project.
6. Run Godot headless/console and fix errors before reporting success.
```

The ready-to-paste agent prompt is:

```text
integration/AI_GODOT_IMPORT_PROMPT.md
```

## Adding more songs later

After the runtime is installed once, each new music level is just another bundle:

```text
res://levels/song_a/
res://levels/song_b/
res://levels/{song_id}/
```

For future songs, the user can simply give an AI agent a new audio file and say:

```text
Generate a RhythmKit bundle from this audio, copy it to res://levels/<new_song_id>/, update the level select/menu entry, and run Godot verification.
```

## Engine-neutral runtime algorithm

```text
1. Load metadata.json.
2. Let the player choose a difficulty.
3. Load metadata.charts[difficulty].
4. Load metadata.audio.
5. Start the audio.
6. Every frame: now = audio_playback_time - chart.offset.
7. Spawn/render notes where note.time - now <= spawn_ahead.
8. On player input lane: find nearest unhit note in the same lane.
9. Compare abs(note.time - now) against chart.difficulty.perfect_window and good_window.
```
"""


def ai_godot_import_prompt(song_id: str, difficulties: list[str]) -> str:
    diffs = ", ".join(difficulties)
    return f"""# AI Prompt: Import RhythmKit Into My Existing Godot Game

You are working inside my existing Godot 4 project. Work autonomously: inspect files, edit the project, run verification, and fix errors. Do not ask me to hand-write GDScript.

I have a generated RhythmKit music-level bundle from `audio-to-rhythm-godot-kit`.

## Bundle

Bundle folder name:

```text
{song_id}
```

Copy/expect it at:

```text
res://levels/{song_id}/
```

It contains:

```text
metadata.json
audio/song.wav
charts/*.chart.json
analysis/report.json
integration/README.md
```

Available difficulties: {diffs}

## Goal

Make my existing Godot game able to play this rhythm level, and leave the project ready so future songs only require adding another `res://levels/<song_id>/` bundle.

## First inspect, then integrate

1. Inspect `project.godot`, the main scene, menus, level select, autoloads, and input map. Do not assume scene names.
2. If the project already has a rhythm system, adapt this bundle to it. Otherwise add the reusable RhythmKit runtime under:

```text
res://addons/rhythmkit/RhythmLevelLoader.gd
res://addons/rhythmkit/RhythmGameView.gd
res://addons/rhythmkit/RhythmGameView.tscn
```

3. Confirm this bundle exists at:

```text
res://levels/{song_id}/metadata.json
res://levels/{song_id}/audio/song.wav
res://levels/{song_id}/charts/*.chart.json
```

4. Add a low-invasive game entry point:

- If a menu or level-select scene exists, add this song as an option there.
- If a specific NPC/map trigger is obvious, connect the rhythm level there.
- If no entry is obvious, create a debug/test scene or button that launches it.
- Do not overwrite existing gameplay scenes unless necessary.

## Required runtime API

Expose or support this usage from the existing game:

```gdscript
var view = preload("res://addons/rhythmkit/RhythmGameView.tscn").instantiate()
add_child(view)
view.load_bundle("res://levels/{song_id}", "normal")
view.start_game()
```

The runtime must:

- load `metadata.json`;
- list/select difficulties from `metadata.charts`;
- load selected `charts/<difficulty>.chart.json`;
- load `audio/song.wav`;
- play audio through `AudioStreamPlayer`;
- render notes using `note.time`, `note.lane`, and `note.type`;
- use `chart.difficulty.note_speed`, `perfect_window`, and `good_window`;
- support the fixed 3-key layout: `A`, `S`, `D` mapped to lanes `0`, `1`, `2`.

## Project documentation you must add

Create or update:

```text
docs/rhythm_bundle_import.md
```

It must explain for future AI agents:

- runtime location: `res://addons/rhythmkit/`;
- level location pattern: `res://levels/<song_id>/`;
- how this imported song is launched;
- how to add a future song from a new audio file;
- how to update the menu/level select/trigger list;
- which visuals/UI can be safely customized.

Include this future-song workflow in the docs:

```text
1. Run audio-to-rhythm-godot-kit on the new audio:
   python scripts/create_rhythm_bundle.py <audio> --difficulties easy,normal,hard --lanes 3 --keys A,S,D --target bundle --out <tmp>/<new_song_id>_bundle
2. Copy the generated bundle to res://levels/<new_song_id>/.
3. Add <new_song_id> to the same menu/level-select/trigger integration used by this song.
4. Run Godot headless/console to verify.
```

## Data contract

`metadata.json`:

```json
{{
  "schema": "com.rhythmkit.bundle.v1",
  "layout": {{"lanes": 3, "keys": ["A", "S", "D"]}},
  "audio": "audio/song.wav",
  "charts": {{
    "easy": "charts/easy.chart.json",
    "normal": "charts/normal.chart.json",
    "hard": "charts/hard.chart.json"
  }}
}}
```

`charts/*.chart.json`:

```json
{{
  "schema": "com.rhythmkit.chart.v1",
  "difficulty": {{
    "name": "normal",
    "lanes": 3,
    "note_speed": 520,
    "perfect_window": 0.06,
    "good_window": 0.12
  }},
  "lanes": [
    {{"id": 0, "name": "CUT", "default_key": "A"}},
    {{"id": 1, "name": "STIR", "default_key": "S"}},
    {{"id": 2, "name": "FIRE", "default_key": "D"}}
  ],
  "notes": [
    {{"id": 1, "time": 1.25, "lane": 0, "type": "tap"}}
  ]
}}
```

## Verification

Run Godot after changes and fix any parser/runtime errors.

Prefer:

```bash
godot --headless --path . --quit-after 30
```

or if available on Windows:

```bash
/d/Godot/Godot_v4.6.1-stable_win64_console.exe --headless --path . --quit-after 30
```

Return only after verification, with:

- files changed;
- where the rhythm level is launched from;
- how future audio files should be handed to AI;
- verification command/output;
- limitations or follow-up tasks.
"""




RHYTHM_BUNDLE_LOADER_GD = r'''class_name RhythmBundleLoader
extends RefCounted

static func read_json(path: String) -> Variant:
	var text = FileAccess.get_file_as_string(path)
	if text == "":
		push_error("Cannot read JSON: " + path)
		return null
	var parsed = JSON.parse_string(text)
	if parsed == null:
		push_error("Invalid JSON: " + path)
	return parsed

static func join_path(base: String, rel: String) -> String:
	if base.ends_with("/"):
		return base + rel
	return base + "/" + rel

static func load_metadata(bundle_path: String) -> Dictionary:
	var data = read_json(join_path(bundle_path, "metadata.json"))
	if typeof(data) != TYPE_DICTIONARY:
		return {}
	return data

static func load_chart(bundle_path: String, difficulty: String) -> Dictionary:
	var metadata = load_metadata(bundle_path)
	if metadata.is_empty():
		return {}
	var charts = metadata.get("charts", {})
	if not charts.has(difficulty):
		var keys = charts.keys()
		if keys.is_empty():
			push_error("No charts in bundle: " + bundle_path)
			return {}
		difficulty = str(keys[0])
	var chart_path = join_path(bundle_path, str(charts[difficulty]))
	var chart = read_json(chart_path)
	if typeof(chart) != TYPE_DICTIONARY:
		return {}
	chart["_bundle_path"] = bundle_path
	chart["_difficulty"] = difficulty
	return chart

static func load_audio_stream(path: String) -> AudioStream:
	var ext = path.get_extension().to_lower()
	if ext == "wav":
		return AudioStreamWAV.load_from_file(path)
	if ext == "mp3":
		return AudioStreamMP3.load_from_file(path)
	if ext == "ogg":
		return AudioStreamOggVorbis.load_from_file(path)
	return load(path)

static func load_bundle_audio(bundle_path: String, metadata: Dictionary) -> AudioStream:
	var audio_rel = str(metadata.get("audio", "audio/song.wav"))
	return load_audio_stream(join_path(bundle_path, audio_rel))
'''


RHYTHM_GAME_VIEW_GD = r'''extends Control

const BundleLoader = preload("res://addons/rhythmkit/RhythmBundleLoader.gd")

@export var bundle_path: String = "res://levels/example_song"
@export var difficulty: String = "normal"
@export var spawn_ahead: float = 2.4

var metadata: Dictionary = {}
var chart: Dictionary = {}
var notes: Array = []
var lanes: Array = []
var lane_count: int = 3
var note_speed: float = 520.0
var perfect_window: float = 0.060
var good_window: float = 0.120
var score: int = 0
var combo: int = 0
var judgement: String = "READY"
var judgement_timer: float = 0.0
var started: bool = false
var lane_keys: Array = []
var lane_labels: Array = []

@onready var music: AudioStreamPlayer = $Music

const FALLBACK_KEYS = [KEY_A, KEY_S, KEY_D]
const COLORS = [
	Color(0.95, 0.40, 0.28, 1.0),
	Color(0.95, 0.67, 0.25, 1.0),
	Color(0.44, 0.80, 0.95, 1.0),
	Color(0.82, 0.38, 0.95, 1.0),
	Color(0.40, 0.90, 0.55, 1.0),
	Color(0.95, 0.95, 0.45, 1.0),
]

func _ready() -> void:
	if bundle_path != "":
		load_bundle(bundle_path, difficulty)

func load_bundle(new_bundle_path: String, new_difficulty: String = "normal") -> void:
	bundle_path = new_bundle_path
	difficulty = new_difficulty
	metadata = BundleLoader.load_metadata(bundle_path)
	chart = BundleLoader.load_chart(bundle_path, difficulty)
	if chart.is_empty():
		judgement = "NO CHART"
		queue_redraw()
		return
	notes = chart.get("notes", [])
	lanes = chart.get("lanes", [])
	lane_count = max(1, lanes.size())
	var diff = chart.get("difficulty", {})
	note_speed = float(diff.get("note_speed", note_speed))
	perfect_window = float(diff.get("perfect_window", perfect_window))
	good_window = float(diff.get("good_window", good_window))
	lane_keys = []
	for i in range(lane_count):
		var key_name = ""
		if i < lanes.size():
			key_name = str(lanes[i].get("default_key", ""))
		lane_keys.append(key_name_to_code(key_name, i))
	for note in notes:
		note["hit"] = false
		note["missed"] = false
	var stream = BundleLoader.load_bundle_audio(bundle_path, metadata)
	if stream != null:
		music.stream = stream
	else:
		judgement = "NO AUDIO"
	build_labels()
	queue_redraw()

func build_labels() -> void:
	for label in lane_labels:
		if is_instance_valid(label):
			label.queue_free()
	lane_labels.clear()
	for i in range(lane_count):
		var label = Label.new()
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.add_theme_font_size_override("font_size", 18)
		add_child(label)
		lane_labels.append(label)

func key_name_to_code(key_name: String, index: int) -> int:
	var up = key_name.to_upper()
	if up.length() == 1:
		return OS.find_keycode_from_string(up)
	if index < FALLBACK_KEYS.size():
		return FALLBACK_KEYS[index]
	return KEY_NONE

func start_game() -> void:
	if music.stream == null:
		judgement = "NO AUDIO"
		return
	for note in notes:
		note["hit"] = false
		note["missed"] = false
	score = 0
	combo = 0
	started = true
	music.play(0.0)
	judgement = "GO"
	judgement_timer = 0.8

func get_song_time() -> float:
	if not music.playing:
		return 0.0
	var t = music.get_playback_position() + AudioServer.get_time_since_last_mix() - AudioServer.get_output_latency()
	return max(0.0, t - float(chart.get("offset", 0.0)))

func _process(delta: float) -> void:
	if judgement_timer > 0.0:
		judgement_timer -= delta
		if judgement_timer <= 0.0:
			judgement = ""
	update_misses()
	queue_redraw()

func update_misses() -> void:
	if not started:
		return
	var now = get_song_time()
	for note in notes:
		if bool(note.get("hit", false)) or bool(note.get("missed", false)):
			continue
		if float(note.get("time", 0.0)) < now - good_window:
			note["missed"] = true
			combo = 0
			judgement = "MISS"
			judgement_timer = 0.15

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_SPACE and not started:
			start_game()
			return
		for i in range(lane_keys.size()):
			if event.keycode == int(lane_keys[i]):
				hit_lane(i)
				return
	if event is InputEventScreenTouch and event.pressed:
		var lane = int(clamp(floor(event.position.x / max(1.0, size.x / float(lane_count))), 0, lane_count - 1))
		hit_lane(lane)

func hit_lane(lane: int) -> void:
	if not started:
		start_game()
		return
	var now = get_song_time()
	var best_index = -1
	var best_delta = 999.0
	for i in range(notes.size()):
		var note: Dictionary = notes[i]
		if int(note.get("lane", 0)) != lane:
			continue
		if bool(note.get("hit", false)) or bool(note.get("missed", false)):
			continue
		var d = abs(float(note.get("time", 0.0)) - now)
		if d < best_delta:
			best_delta = d
			best_index = i
	if best_index == -1 or best_delta > good_window:
		combo = 0
		judgement = "MISS"
		judgement_timer = 0.20
		return
	notes[best_index]["hit"] = true
	combo += 1
	if best_delta <= perfect_window:
		score += 1000 + combo * 8
		judgement = "PERFECT"
	else:
		score += 500 + combo * 4
		judgement = "GOOD"
	judgement_timer = 0.30

func _draw() -> void:
	var w = max(size.x, 1.0)
	var h = max(size.y, 1.0)
	var lane_w = w / float(max(lane_count, 1))
	var play_top = 100.0
	var hit_y = h - 145.0
	var now = get_song_time()
	draw_rect(Rect2(Vector2.ZERO, Vector2(w, h)), Color(0.08, 0.06, 0.07, 1), true)
	for i in range(lane_count):
		var x = i * lane_w
		var color: Color = COLORS[i % COLORS.size()]
		draw_rect(Rect2(Vector2(x + 2, play_top), Vector2(lane_w - 4, hit_y - play_top + 75)), Color(color.r, color.g, color.b, 0.10), true)
		draw_line(Vector2(x, play_top), Vector2(x, h), Color(1, 1, 1, 0.12), 2)
		draw_rect(Rect2(Vector2(x + lane_w * 0.15, hit_y - 8), Vector2(lane_w * 0.70, 16)), color, true)
		if i < lane_labels.size():
			var label: Label = lane_labels[i]
			label.position = Vector2(x + 4, h - 82)
			label.size = Vector2(lane_w - 8, 46)
			var lane_name = str(lanes[i].get("name", "LANE")) if i < lanes.size() else "LANE"
			var key_text = OS.get_keycode_string(int(lane_keys[i])) if i < lane_keys.size() else ""
			label.text = lane_name + "\n[" + key_text + "]"
	for note in notes:
		if bool(note.get("hit", false)) or bool(note.get("missed", false)):
			continue
		var t = float(note.get("time", 0.0))
		if t < now - good_window or t > now + spawn_ahead:
			continue
		var lane = int(clamp(int(note.get("lane", 0)), 0, lane_count - 1))
		var y = hit_y - (t - now) * note_speed
		var x_center = lane * lane_w + lane_w * 0.5
		var color: Color = COLORS[lane % COLORS.size()]
		var radius = min(lane_w * 0.28, 42.0)
		draw_circle(Vector2(x_center, y), radius, color)
		draw_circle(Vector2(x_center, y), radius * 0.55, Color(1, 0.92, 0.72, 0.78))
	draw_string(ThemeDB.fallback_font, Vector2(24, 42), "Score %d  Combo %d" % [score, combo], HORIZONTAL_ALIGNMENT_LEFT, -1, 28, Color.WHITE)
	draw_string(ThemeDB.fallback_font, Vector2(w * 0.5 - 80, h * 0.45), judgement, HORIZONTAL_ALIGNMENT_CENTER, 160, 42, Color(1.0, 0.78, 0.28, 1.0))
'''


RHYTHM_GAME_VIEW_TSCN = '''[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://addons/rhythmkit/RhythmGameView.gd" id="1"]

[node name="RhythmGameView" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
script = ExtResource("1")

[node name="Music" type="AudioStreamPlayer" parent="."]
'''


def write_godot_addon(root_dir: Path, *, default_song_id: str | None = None, default_difficulty: str = "normal") -> None:
    addon = root_dir / "addons" / "rhythmkit"
    write_text(addon / "RhythmBundleLoader.gd", RHYTHM_BUNDLE_LOADER_GD)
    view_gd = RHYTHM_GAME_VIEW_GD
    if default_song_id:
        view_gd = view_gd.replace('res://levels/example_song', f'res://levels/{default_song_id}')
    view_gd = view_gd.replace('@export var difficulty: String = "normal"', f'@export var difficulty: String = "{default_difficulty}"')
    write_text(addon / "RhythmGameView.gd", view_gd)
    write_text(addon / "RhythmGameView.tscn", RHYTHM_GAME_VIEW_TSCN)
    write_text(
        addon / "README.md",
        """# RhythmKit Godot Runtime

Copy `addons/rhythmkit` into a Godot 4 project, then copy generated bundles into `res://levels/<song_id>/`.

```gdscript
var view = preload("res://addons/rhythmkit/RhythmGameView.tscn").instantiate()
add_child(view)
view.load_bundle("res://levels/<song_id>", "normal")
view.start_game()
```

This runtime is intentionally simple. Your game should replace visuals/scoring/menu integration as needed.
""",
    )


def write_project_godot(root_dir: Path, project_name: str, main_scene: str) -> None:
    write_text(
        root_dir / "project.godot",
        f'''; Engine configuration file.
; Generated by audio-to-rhythm-godot-kit.

config_version=5

[application]

config/name="{project_name}"
run/main_scene="{main_scene}"
config/features=PackedStringArray("4.6")

[display]

window/size/viewport_width=900
window/size/viewport_height=1400
window/stretch/mode="canvas_items"
window/stretch/aspect="expand"

[rendering]

renderer/rendering_method="gl_compatibility"
''',
    )


def create_bundle(
    *,
    audio_path: str | Path,
    out_dir: str | Path,
    presets: list[DifficultyPreset],
    title: str | None = None,
    artist: str | None = None,
    song_id: str | None = None,
    theme: str = "cooking",
    keys: list[str] | tuple[str, ...] | None = None,
    include_original: bool = True,
) -> dict[str, Any]:
    audio_path = Path(audio_path).resolve()
    out_dir = Path(out_dir).resolve()
    keys = list(keys) if keys is not None else list(DEFAULT_KEYS)
    title = title or audio_path.stem
    song_id = song_id or slugify(title)

    audio_dir = out_dir / "audio"
    charts_dir = out_dir / "charts"
    analysis_dir = out_dir / "analysis"
    integration_dir = out_dir / "integration"
    audio_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    integration_dir.mkdir(parents=True, exist_ok=True)

    normalized_audio = audio_dir / "song.wav"
    convert_audio_for_bundle(audio_path, normalized_audio)
    original_rel = None
    if include_original:
        original_target = audio_dir / ("original" + audio_path.suffix.lower())
        shutil.copy2(audio_path, original_target)
        original_rel = str(original_target.relative_to(out_dir)).replace("\\", "/")

    duration_hint = probe_duration(audio_path)
    charts: dict[str, str] = {}
    chart_reports: dict[str, Any] = {}
    bpm_values: list[float] = []
    duration = duration_hint or 0.0

    for preset in presets:
        max_notes = preset.max_notes_for_duration(duration_hint or 30.0)
        raw_chart, report = generate_chart(
            audio_path,
            title=title,
            theme=theme,
            lanes=preset.lanes,
            keys=keys,
            max_notes=max_notes,
            min_gap_s=preset.min_gap,
        )
        chart = normalize_chart_for_bundle(raw_chart, song_id=song_id, title=title, artist=artist, preset=preset)
        chart_path = charts_dir / f"{preset.name}.chart.json"
        write_json(chart_path, chart)
        charts[preset.name] = str(chart_path.relative_to(out_dir)).replace("\\", "/")
        chart_reports[preset.name] = {
            "difficulty": preset.to_chart_dict(),
            "notes": len(chart.get("notes", [])),
            "max_notes": max_notes,
            "min_gap": preset.min_gap,
            "bpm": chart.get("bpm"),
            "duration": chart.get("duration"),
            "analysis_report": report,
        }
        bpm_values.append(float(chart.get("bpm", 0.0)))
        duration = float(chart.get("duration", duration or 0.0))

    bpm = round(sum(bpm_values) / len(bpm_values), 2) if bpm_values else 120.0
    metadata = {
        "schema": BUNDLE_SCHEMA,
        "generator": GENERATOR_NAME,
        "generator_version": GENERATOR_VERSION,
        "song_id": song_id,
        "title": title,
        "artist": artist or "",
        "audio": "audio/song.wav",
        "original_audio": original_rel or "",
        "duration": round(duration, 4),
        "bpm": bpm,
        "theme": theme,
        "layout": {"lanes": presets[0].lanes if presets else 0, "keys": list(keys or [])},
        "charts": charts,
    }
    write_json(out_dir / "metadata.json", metadata)
    report = {
        "schema": "com.rhythmkit.analysis_report.v1",
        "source_audio": str(audio_path),
        "bundle": str(out_dir),
        "metadata": metadata,
        "charts": chart_reports,
        "dependencies": {"ffmpeg": find_ffmpeg_optional()},
        "limitations": [
            "MVP uses onset/energy analysis, not full melody transcription.",
            "Keysounds are not extracted from mixed audio in this version.",
        ],
    }
    write_json(analysis_dir / "report.json", report)
    write_text(integration_dir / "README.md", integration_readme(song_id, list(charts.keys())))
    write_text(integration_dir / "AI_GODOT_IMPORT_PROMPT.md", ai_godot_import_prompt(song_id, list(charts.keys())))
    return {"bundle": str(out_dir), "metadata": metadata, "report": report}


def zip_directory(dir_path: str | Path) -> str:
    dir_path = Path(dir_path).resolve()
    archive = shutil.make_archive(str(dir_path), "zip", root_dir=dir_path)
    return archive
