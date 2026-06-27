class_name RhythmBundleLoader
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
