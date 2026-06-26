extends Control
class_name RhythmGameView

@export var bundle_path: String = ""
@export var difficulty: String = "normal"
@export var auto_start: bool = false
@export var fallback_note_speed: float = 520.0

var chart: Dictionary = {}
var notes: Array = []
var lane_data: Array = []
var lane_count: int = 3
var note_speed: float = 520.0
var spawn_ahead: float = 2.4
var perfect_window: float = 0.06
var good_window: float = 0.12
var score: int = 0
var combo: int = 0
var max_combo: int = 0
var hits: int = 0
var misses: int = 0
var judgement: String = "READY"
var judgement_timer: float = 0.0
var started: bool = false
var lane_labels: Array = []
var active_holds: Dictionary = {}
var touch_lanes: Dictionary = {}

@onready var music: AudioStreamPlayer = $Music

const LOADER = preload("res://addons/rhythmkit/RhythmLevelLoader.gd")
const KEY_CODES = [KEY_A, KEY_S, KEY_D]
const LANE_COLORS = [
	Color(0.95, 0.40, 0.28, 1.0),
	Color(0.95, 0.67, 0.25, 1.0),
	Color(0.44, 0.80, 0.95, 1.0),
	Color(0.82, 0.38, 0.95, 1.0),
	Color(0.40, 0.90, 0.55, 1.0),
	Color(0.95, 0.95, 0.45, 1.0),
]

var score_label: Label
var combo_label: Label
var judgement_label: Label

func _ready() -> void:
	if bundle_path != "":
		load_bundle(bundle_path, difficulty)
	build_ui()
	if auto_start and not chart.is_empty():
		start_game()
	queue_redraw()

func load_bundle(path: String, selected_difficulty: String = "normal") -> void:
	bundle_path = path
	difficulty = selected_difficulty
	chart = LOADER.load_bundle(path, selected_difficulty)
	if chart.is_empty():
		return
	notes = chart.get("notes", [])
	lane_data = chart.get("lanes", [])
	lane_count = max(1, lane_data.size())
	reset_note_state()
	var diff = chart.get("difficulty", {})
	if typeof(diff) == TYPE_DICTIONARY:
		note_speed = float(diff.get("note_speed", fallback_note_speed))
		spawn_ahead = float(diff.get("spawn_ahead", spawn_ahead))
		perfect_window = float(diff.get("perfect_window", perfect_window))
		good_window = float(diff.get("good_window", good_window))
	var audio_path = str(chart.get("_audio_path", ""))
	var stream = LOADER.load_audio_stream(audio_path)
	if stream != null:
		music.stream = stream
	else:
		push_error("RhythmKit: cannot load audio: " + audio_path)
	queue_redraw()

func reset_note_state() -> void:
	active_holds.clear()
	touch_lanes.clear()
	for note in notes:
		note["hit"] = false
		note["missed"] = false
		note["holding"] = false

func build_ui() -> void:
	if score_label != null:
		return
	score_label = Label.new()
	score_label.add_theme_font_size_override("font_size", 28)
	add_child(score_label)
	combo_label = Label.new()
	combo_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	combo_label.add_theme_font_size_override("font_size", 30)
	add_child(combo_label)
	judgement_label = Label.new()
	judgement_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	judgement_label.add_theme_font_size_override("font_size", 44)
	add_child(judgement_label)
	lane_labels.clear()
	for i in range(lane_count):
		var label = Label.new()
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.add_theme_font_size_override("font_size", 20)
		add_child(label)
		lane_labels.append(label)
	update_ui_labels()

func start_game() -> void:
	if music.stream == null:
		judgement = "NO AUDIO"
		return
	reset_note_state()
	score = 0
	combo = 0
	max_combo = 0
	hits = 0
	misses = 0
	started = true
	music.play(0.0)
	judgement = "GO"
	judgement_timer = 0.8

func stop_game() -> void:
	started = false
	active_holds.clear()
	music.stop()

func get_song_time() -> float:
	if not music.playing:
		return 0.0
	var t = music.get_playback_position() + AudioServer.get_time_since_last_mix() - AudioServer.get_output_latency()
	return max(0.0, t - float(chart.get("offset", 0.0)))

func is_hold_note(note: Dictionary) -> bool:
	return str(note.get("type", "tap")) == "hold" and float(note.get("duration", 0.0)) > 0.0

func note_end_time(note: Dictionary) -> float:
	return float(note.get("time", 0.0)) + (float(note.get("duration", 0.0)) if is_hold_note(note) else 0.0)

func _process(delta: float) -> void:
	if judgement_timer > 0.0:
		judgement_timer -= delta
		if judgement_timer <= 0.0 and judgement != "READY":
			judgement = ""
	update_misses()
	update_ui_labels()
	queue_redraw()

func update_misses() -> void:
	if not started:
		return
	var now = get_song_time()
	for note in notes:
		if bool(note.get("hit", false)) or bool(note.get("missed", false)):
			continue
		if bool(note.get("holding", false)):
			if now >= note_end_time(note) - perfect_window:
				complete_hold(note, abs(note_end_time(note) - now))
			continue
		if float(note.get("time", 0.0)) < now - good_window:
			mark_miss(note)

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
	if event is InputEventKey and not event.echo:
		for i in range(min(lane_count, KEY_CODES.size())):
			if event.keycode == KEY_CODES[i]:
				if event.pressed:
					hit_lane(i)
				else:
					release_lane(i)
				return
		if event.pressed and event.keycode == KEY_SPACE and not started:
			start_game()
	if event is InputEventScreenTouch:
		var lane = int(clamp(floor(event.position.x / max(1.0, size.x / float(lane_count))), 0, lane_count - 1))
		if event.pressed:
			touch_lanes[event.index] = lane
			hit_lane(lane)
		else:
			var held_lane = int(touch_lanes.get(event.index, lane))
			touch_lanes.erase(event.index)
			release_lane(held_lane)

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
		if bool(note.get("hit", false)) or bool(note.get("missed", false)) or bool(note.get("holding", false)):
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
	var note: Dictionary = notes[best_index]
	if is_hold_note(note):
		note["holding"] = true
		active_holds[lane] = note
		judgement = "HOLD"
		judgement_timer = 0.25
		return
	complete_tap(note, best_delta)

func release_lane(lane: int) -> void:
	if not active_holds.has(lane):
		return
	var note: Dictionary = active_holds[lane]
	var now = get_song_time()
	var end_delta = abs(note_end_time(note) - now)
	active_holds.erase(lane)
	if now >= note_end_time(note) - good_window:
		complete_hold(note, end_delta)
	else:
		mark_miss(note)

func complete_tap(note: Dictionary, delta: float) -> void:
	note["hit"] = true
	hits += 1
	combo += 1
	max_combo = max(max_combo, combo)
	if delta <= perfect_window:
		score += 1000 + combo * 8
		judgement = "PERFECT"
	else:
		score += 500 + combo * 4
		judgement = "GOOD"
	judgement_timer = 0.35

func complete_hold(note: Dictionary, end_delta: float) -> void:
	if bool(note.get("hit", false)) or bool(note.get("missed", false)):
		return
	var lane = int(note.get("lane", 0))
	active_holds.erase(lane)
	note["holding"] = false
	note["hit"] = true
	hits += 1
	combo += 1
	max_combo = max(max_combo, combo)
	if end_delta <= perfect_window:
		score += 1250 + combo * 10
		judgement = "PERFECT HOLD"
	else:
		score += 700 + combo * 6
		judgement = "GOOD HOLD"
	judgement_timer = 0.35

func mark_miss(note: Dictionary) -> void:
	var lane = int(note.get("lane", 0))
	active_holds.erase(lane)
	note["holding"] = false
	note["missed"] = true
	combo = 0
	misses += 1
	judgement = "MISS"
	judgement_timer = 0.18

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
		draw_rect(Rect2(Vector2(x + 2, play_top), Vector2(lane_w - 4, hit_y - play_top + 70)), Color(lane_col.r, lane_col.g, lane_col.b, 0.10), true)
		draw_line(Vector2(x, play_top), Vector2(x, h), Color(1, 1, 1, 0.12), 2.0)
		draw_rect(Rect2(Vector2(x + lane_w * 0.12, hit_y - 8), Vector2(lane_w * 0.76, 16)), Color(lane_col.r, lane_col.g, lane_col.b, 0.90), true)
	draw_line(Vector2(w, play_top), Vector2(w, h), Color(1, 1, 1, 0.12), 2.0)
	for note in notes:
		if bool(note.get("hit", false)) or bool(note.get("missed", false)):
			continue
		var t = float(note.get("time", 0.0))
		var end_t = note_end_time(note)
		if end_t < now - good_window or t > now + spawn_ahead:
			continue
		var lane = int(clamp(int(note.get("lane", 0)), 0, lane_count - 1))
		var y = hit_y if bool(note.get("holding", false)) else hit_y - (t - now) * note_speed
		if y < play_top - 160.0 or y > h + 160.0:
			continue
		var x_center = lane * lane_w + lane_w * 0.5
		var col: Color = LANE_COLORS[lane % LANE_COLORS.size()]
		var radius = min(lane_w * 0.30, 46.0)
		if is_hold_note(note):
			var tail_y = hit_y - (end_t - now) * note_speed
			var top_y = clamp(min(y, tail_y), play_top - 120.0, h + 120.0)
			var bottom_y = clamp(max(y, tail_y), play_top - 120.0, h + 120.0)
			var body_color = Color(col.r, col.g, col.b, 0.72 if bool(note.get("holding", false)) else 0.46)
			draw_rect(Rect2(Vector2(x_center - radius * 0.42, top_y), Vector2(radius * 0.84, max(12.0, bottom_y - top_y))), body_color, true)
			draw_circle(Vector2(x_center, tail_y), radius * 0.48, Color(1.0, 0.86, 0.42, 0.90))
		draw_circle(Vector2(x_center, y), radius, Color(col.r, col.g, col.b, 0.95))
		draw_circle(Vector2(x_center, y), radius * 0.58, Color(1.0, 0.92, 0.72, 0.78))
	var dur = float(chart.get("duration", 0.0))
	if dur > 0.0:
		var progress = clamp(now / dur, 0.0, 1.0)
		draw_rect(Rect2(Vector2(24, 76), Vector2(w - 48, 6)), Color(1, 1, 1, 0.18), true)
		draw_rect(Rect2(Vector2(24, 76), Vector2((w - 48) * progress, 6)), Color(1.0, 0.72, 0.26, 1.0), true)
