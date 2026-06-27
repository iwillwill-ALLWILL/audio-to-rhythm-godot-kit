extends RefCounted
class_name RhythmBundleLoader

static func _join_path(base_path: String, relative_path: String) -> String:
	if relative_path.begins_with("res://") or relative_path.begins_with("user://"):
		return relative_path
	return base_path.path_join(relative_path)

static func load_json(path: String) -> Dictionary:
	var text = FileAccess.get_file_as_string(path)
	if text == "":
		push_error("RhythmKit: cannot read JSON: " + path)
		return {}
	var parsed = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("RhythmKit: invalid JSON object: " + path)
		return {}
	return parsed

static func load_metadata(bundle_path: String) -> Dictionary:
	return load_json(bundle_path.path_join("metadata.json"))

static func pick_first_difficulty(metadata: Dictionary) -> String:
	var charts = metadata.get("charts", {})
	if typeof(charts) != TYPE_DICTIONARY or charts.is_empty():
		return ""
	if charts.has("normal"):
		return "normal"
	return str(charts.keys()[0])

static func load_bundle(bundle_path: String, difficulty: String = "normal") -> Dictionary:
	var metadata = load_metadata(bundle_path)
	if metadata.is_empty():
		return {}
	var charts = metadata.get("charts", {})
	if typeof(charts) != TYPE_DICTIONARY or charts.is_empty():
		push_error("RhythmKit: metadata has no charts dictionary")
		return {}
	var selected = difficulty
	if not charts.has(selected):
		selected = pick_first_difficulty(metadata)
		push_warning("RhythmKit: requested difficulty not found, using " + selected)
	var chart_path = _join_path(bundle_path, str(charts[selected]))
	var chart = load_json(chart_path)
	if chart.is_empty():
		return {}
	chart["_bundle_path"] = bundle_path
	chart["_chart_path"] = chart_path
	chart["_metadata"] = metadata
	chart["_selected_difficulty"] = selected
	chart["_audio_path"] = _join_path(bundle_path, str(metadata.get("audio", chart.get("audio", ""))))
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
