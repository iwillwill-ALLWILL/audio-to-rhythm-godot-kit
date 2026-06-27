# AI Prompt: Import RhythmKit Into My Existing Godot Game

You are working inside my existing Godot 4 project. Work autonomously: inspect files, edit the project, run verification, and fix errors. Do not ask me to hand-write GDScript.

I have a generated RhythmKit music-level bundle from `audio-to-rhythm-godot-kit`.

## Bundle

Bundle folder name:

```text
ready_expert_demo
```

Copy/expect it at:

```text
res://levels/ready_expert_demo/
```

It contains:

```text
metadata.json
audio/song.wav
charts/*.chart.json
analysis/report.json
integration/README.md
```

Available difficulties: expert

## Goal

Make my existing Godot game able to play this rhythm level, and leave the project ready so future songs only require adding another `res://levels/<song_id>/` bundle.

## First inspect, then integrate

1. Inspect `project.godot`, the main scene, menus, level select, autoloads, and input map. Do not assume scene names.
2. If the project already has a rhythm system, adapt this bundle to it. Otherwise add the reusable RhythmKit runtime under:

```text
res://addons/rhythmkit/RhythmBundleLoader.gd
res://addons/rhythmkit/RhythmGameView.gd
res://addons/rhythmkit/RhythmGameView.tscn
```

3. Confirm this bundle exists at:

```text
res://levels/ready_expert_demo/metadata.json
res://levels/ready_expert_demo/audio/song.wav
res://levels/ready_expert_demo/charts/*.chart.json
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
view.load_bundle("res://levels/ready_expert_demo", "expert")
view.start_game()
```

The runtime must:

- load `metadata.json`;
- list/select difficulties from `metadata.charts`;
- load selected `charts/<difficulty>.chart.json`;
- load `audio/song.wav`;
- play audio through `AudioStreamPlayer`;
- render notes using `note.time`, `note.lane`, `note.type`, and `note.duration` for holds;
- support simultaneous notes when multiple notes share the same `note.time` on different lanes;
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
{
  "schema": "com.rhythmkit.bundle.v1",
  "layout": {"lanes": 3, "keys": ["A", "S", "D"]},
  "audio": "audio/song.wav",
  "charts": {
    "expert": "charts/expert.chart.json"
  }
}
```

`charts/*.chart.json`:

```json
{
  "schema": "com.rhythmkit.chart.v1",
  "difficulty": {
    "name": "expert",
    "lanes": 3,
    "note_speed": 520,
    "perfect_window": 0.06,
    "good_window": 0.12
  },
  "lanes": [
    {"id": 0, "name": "CUT", "default_key": "A"},
    {"id": 1, "name": "STIR", "default_key": "S"},
    {"id": 2, "name": "FIRE", "default_key": "D"}
  ],
  "notes": [
    {"id": 1, "time": 1.25, "lane": 0, "type": "tap"},
    {"id": 2, "time": 2.00, "lane": 1, "type": "hold", "duration": 0.55}
  ]
}
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
