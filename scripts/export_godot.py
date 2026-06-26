#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

from analyze_audio import decode_pcm_wav


GODOT_SCRIPT = r'''extends Control

@export var chart_path: String = "res://assets/rhythm/chart.json"
@export var audio_path: String = ""
@export var note_speed: float = 520.0
@export var spawn_ahead: float = 2.4
@export var perfect_window: float = 0.055
@export var good_window: float = 0.12
@export var auto_start: bool = true

var chart: Dictionary = {}
var notes: Array = []
var lane_data: Array = []
var lane_count: int = 3
var score: int = 0
var combo: int = 0
var max_combo: int = 0
var hits: int = 0
var misses: int = 0
var judgement: String = "READY"
var judgement_timer: float = 0.0
var started: bool = false

var score_label: Label
var combo_label: Label
var judgement_label: Label
var lane_labels: Array = []

@onready var music: AudioStreamPlayer = $Music

const KEY_CODES = [KEY_A, KEY_S, KEY_D]
const LANE_COLORS = [
	Color(0.95, 0.40, 0.28, 1.0),
	Color(0.95, 0.67, 0.25, 1.0),
	Color(0.44, 0.80, 0.95, 1.0),
	Color(0.82, 0.38, 0.95, 1.0),
	Color(0.40, 0.90, 0.55, 1.0),
	Color(0.95, 0.95, 0.45, 1.0),
]

func _ready() -> void:
	load_chart()
	build_ui()
	if auto_start:
		start_game()
	queue_redraw()

func load_chart() -> void:
	var text = FileAccess.get_file_as_string(chart_path)
	if text == "":
		push_error("Cannot read chart: " + chart_path)
		return
	var parsed = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("Invalid chart JSON: " + chart_path)
		return
	chart = parsed
	var diff = chart.get("difficulty", {})
	if typeof(diff) == TYPE_DICTIONARY:
		note_speed = float(diff.get("note_speed", note_speed))
		spawn_ahead = float(diff.get("spawn_ahead", spawn_ahead))
		perfect_window = float(diff.get("perfect_window", perfect_window))
		good_window = float(diff.get("good_window", good_window))
	notes = chart.get("notes", [])
	lane_data = chart.get("lanes", [])
	lane_count = max(1, lane_data.size())
	for note in notes:
		note["hit"] = false
		note["missed"] = false
	if audio_path == "":
		audio_path = str(chart.get("audio", ""))
	if audio_path != "":
		var stream = load_audio_stream(audio_path)
		if stream != null:
			music.stream = stream
		else:
			push_error("Cannot load audio: " + audio_path)

func load_audio_stream(path: String) -> AudioStream:
	var ext = path.get_extension().to_lower()
	if ext == "wav":
		return AudioStreamWAV.load_from_file(path)
	if ext == "mp3":
		return AudioStreamMP3.load_from_file(path)
	if ext == "ogg":
		return AudioStreamOggVorbis.load_from_file(path)
	return load(path)

func build_ui() -> void:
	score_label = Label.new()
	score_label.name = "ScoreLabel"
	score_label.add_theme_font_size_override("font_size", 28)
	add_child(score_label)

	combo_label = Label.new()
	combo_label.name = "ComboLabel"
	combo_label.add_theme_font_size_override("font_size", 30)
	add_child(combo_label)

	judgement_label = Label.new()
	judgement_label.name = "JudgementLabel"
	judgement_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	judgement_label.add_theme_font_size_override("font_size", 44)
	add_child(judgement_label)

	lane_labels.clear()
	for i in range(lane_count):
		var label = Label.new()
		label.name = "LaneLabel%d" % i
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.add_theme_font_size_override("font_size", 22)
		add_child(label)
		lane_labels.append(label)
	update_ui_labels()

func start_game() -> void:
	if music.stream == null:
		judgement = "NO AUDIO"
		return
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
		if judgement_timer <= 0.0 and judgement != "READY":
			judgement = ""
	update_misses()
	update_ui_labels()
	queue_redraw()

func update_misses() -> void:
	var now = get_song_time()
	for note in notes:
		if bool(note.get("hit", false)) or bool(note.get("missed", false)):
			continue
		var note_time = float(note.get("time", 0.0))
		if note_time < now - good_window:
			note["missed"] = true
			combo = 0
			misses += 1
			judgement = "MISS"
			judgement_timer = 0.18

func update_ui_labels() -> void:
	if score_label == null:
		return
	var w = max(size.x, 1.0)
	var h = max(size.y, 1.0)
	score_label.position = Vector2(24, 20)
	score_label.size = Vector2(w * 0.5, 42)
	score_label.text = "Score %d" % score
	combo_label.position = Vector2(w - 260, 20)
	combo_label.size = Vector2(236, 44)
	combo_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	combo_label.text = "Combo %d" % combo
	judgement_label.position = Vector2(0, h * 0.43)
	judgement_label.size = Vector2(w, 70)
	judgement_label.text = judgement

	var lane_w = w / float(max(lane_count, 1))
	for i in range(lane_labels.size()):
		var label: Label = lane_labels[i]
		var lane_name = "LANE"
		var key_name = str(KEY_CODES[i])
		if i < lane_data.size():
			lane_name = str(lane_data[i].get("name", lane_name))
			key_name = str(lane_data[i].get("default_key", lane_data[i].get("key", key_name)))
		label.position = Vector2(i * lane_w + 4, h - 82)
		label.size = Vector2(lane_w - 8, 36)
		label.text = "%s\n[%s]" % [lane_name, key_name]

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		for i in range(min(lane_count, KEY_CODES.size())):
			if event.keycode == KEY_CODES[i]:
				hit_lane(i)
				return
		if event.keycode == KEY_SPACE and not started:
			start_game()
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
		judgement_timer = 0.25
		misses += 1
		return
	notes[best_index]["hit"] = true
	hits += 1
	combo += 1
	max_combo = max(max_combo, combo)
	if best_delta <= perfect_window:
		score += 1000 + combo * 8
		judgement = "PERFECT"
	else:
		score += 500 + combo * 4
		judgement = "GOOD"
	judgement_timer = 0.35

func _draw() -> void:
	var w = max(size.x, 1.0)
	var h = max(size.y, 1.0)
	var lane_w = w / float(max(lane_count, 1))
	var play_top = 110.0
	var hit_y = h - 150.0
	var now = get_song_time()

	draw_rect(Rect2(Vector2.ZERO, Vector2(w, h)), Color(0.09, 0.055, 0.07, 1.0), true)
	draw_rect(Rect2(Vector2(0, 0), Vector2(w, 92)), Color(0.18, 0.10, 0.09, 1.0), true)

	for i in range(lane_count):
		var x = i * lane_w
		var lane_col: Color = LANE_COLORS[i % LANE_COLORS.size()]
		var bg_col = Color(lane_col.r, lane_col.g, lane_col.b, 0.10 if i % 2 == 0 else 0.06)
		draw_rect(Rect2(Vector2(x + 2, play_top), Vector2(lane_w - 4, hit_y - play_top + 70)), bg_col, true)
		draw_line(Vector2(x, play_top), Vector2(x, h), Color(1, 1, 1, 0.12), 2.0)
		draw_rect(Rect2(Vector2(x + lane_w * 0.12, hit_y - 8), Vector2(lane_w * 0.76, 16)), Color(lane_col.r, lane_col.g, lane_col.b, 0.90), true)
	draw_line(Vector2(w, play_top), Vector2(w, h), Color(1, 1, 1, 0.12), 2.0)

	for note in notes:
		if bool(note.get("hit", false)) or bool(note.get("missed", false)):
			continue
		var t = float(note.get("time", 0.0))
		if t < now - good_window or t > now + spawn_ahead:
			continue
		var lane = int(clamp(int(note.get("lane", 0)), 0, lane_count - 1))
		var y = hit_y - (t - now) * note_speed
		if y < play_top - 100.0 or y > h + 100.0:
			continue
		var x_center = lane * lane_w + lane_w * 0.5
		var col: Color = LANE_COLORS[lane % LANE_COLORS.size()]
		var radius = min(lane_w * 0.30, 46.0)
		var note_type = str(note.get("type", "tap"))
		if note_type == "hold":
			var dur = float(note.get("duration", 0.5))
			var y2 = hit_y - (t + dur - now) * note_speed
			var top_y = min(y, y2)
			var height = max(20.0, abs(y2 - y))
			draw_rect(Rect2(Vector2(x_center - radius * 0.55, top_y), Vector2(radius * 1.1, height)), Color(col.r, col.g, col.b, 0.55), true)
		draw_circle(Vector2(x_center, y), radius, Color(col.r, col.g, col.b, 0.95))
		draw_circle(Vector2(x_center, y), radius * 0.58, Color(1.0, 0.92, 0.72, 0.78))

	# Song progress bar.
	var dur = float(chart.get("duration", 0.0))
	if dur > 0.0:
		var progress = clamp(now / dur, 0.0, 1.0)
		draw_rect(Rect2(Vector2(24, 76), Vector2(w - 48, 6)), Color(1, 1, 1, 0.18), true)
		draw_rect(Rect2(Vector2(24, 76), Vector2((w - 48) * progress, 6)), Color(1.0, 0.72, 0.26, 1.0), true)
'''


TSCN = '''[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://scripts/RhythmGame.gd" id="1"]

[node name="RhythmGame" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
script = ExtResource("1")
chart_path = "res://assets/rhythm/chart.json"

[node name="Music" type="AudioStreamPlayer" parent="."]
'''


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def find_ffmpeg() -> str:
    env = os.environ.get("FFMPEG") or os.environ.get("FFMPEG_PATH")
    if env and Path(env).exists():
        return env
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    raise RuntimeError("ffmpeg not found on PATH; needed to export Godot-loadable PCM WAV. Install ffmpeg or set FFMPEG/FFMPEG_PATH.")


def find_ffmpeg_optional() -> str | None:
    try:
        return find_ffmpeg()
    except RuntimeError:
        return None


def convert_audio_for_godot(src: Path, dst: Path) -> None:
    """Convert arbitrary input audio to Godot-friendly PCM s16le WAV."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg_optional()
    if ffmpeg is None:
        if src.suffix.lower() != ".wav":
            raise RuntimeError("ffmpeg not found on PATH. Non-WAV Godot exports require ffmpeg or FFMPEG/FFMPEG_PATH.")
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


def export_godot_project(chart_path: str | Path, audio_path: str | Path, out_dir: str | Path, project_name: str | None = None) -> dict:
    chart_path = Path(chart_path).resolve()
    audio_path = Path(audio_path).resolve()
    out_dir = Path(out_dir).resolve()
    project_name = project_name or out_dir.name

    assets_dir = out_dir / "assets" / "rhythm"
    scripts_dir = out_dir / "scripts"
    scenes_dir = out_dir / "scenes"
    assets_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)
    scenes_dir.mkdir(parents=True, exist_ok=True)

    audio_target = assets_dir / "song.wav"
    convert_audio_for_godot(audio_path, audio_target)

    chart = json.loads(chart_path.read_text(encoding="utf-8"))
    chart["audio"] = "res://assets/rhythm/" + audio_target.name
    chart["chart_path"] = "res://assets/rhythm/chart.json"
    chart_target = assets_dir / "chart.json"
    write_text(chart_target, json.dumps(chart, ensure_ascii=False, indent=2))

    project_godot = f'''; Engine configuration file.
; Generated by audio-to-rhythm-godot-kit.

config_version=5

[application]

config/name="{project_name}"
run/main_scene="res://scenes/RhythmGame.tscn"
config/features=PackedStringArray("4.6")

[display]

window/size/viewport_width=900
window/size/viewport_height=1400
window/stretch/mode="canvas_items"
window/stretch/aspect="expand"

[rendering]

renderer/rendering_method="gl_compatibility"
'''
    write_text(out_dir / "project.godot", project_godot)
    write_text(scripts_dir / "RhythmGame.gd", GODOT_SCRIPT)
    write_text(scenes_dir / "RhythmGame.tscn", TSCN)

    manifest = {
        "project": str(out_dir),
        "project_godot": str(out_dir / "project.godot"),
        "scene": "res://scenes/RhythmGame.tscn",
        "chart": str(chart_target),
        "audio": str(audio_target),
        "notes": len(chart.get("notes", [])),
        "bpm": chart.get("bpm"),
        "theme": chart.get("theme"),
    }
    write_text(out_dir / "export_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description="Export a generated rhythm chart as a standalone Godot 4 project")
    ap.add_argument("chart")
    ap.add_argument("audio")
    ap.add_argument("--out", required=True)
    ap.add_argument("--project-name", default=None)
    args = ap.parse_args()
    manifest = export_godot_project(args.chart, args.audio, args.out, args.project_name)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
