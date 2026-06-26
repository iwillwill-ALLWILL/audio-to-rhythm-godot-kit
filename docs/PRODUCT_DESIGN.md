# Audio-to-Rhythm Middleware Product Design

## Positioning

This project is **not** the user's final game. It is a middleware/converter:

```text
User audio file
  -> rhythm analysis + chart generation
  -> portable rhythm level bundle
  -> optional engine-specific preview/import package
```

The converter must stay flexible. It should never assume the user's game is the bundled Godot demo. The Godot demo is only a reference player and integration example.

## Core Output Contract

The primary output is a **level bundle**, not a full game project.

```text
<song_slug>_rhythm_bundle/
  metadata.json
  audio/
    song.wav                 # normalized engine-friendly audio
    original.ext             # optional original upload copy
  charts/
    easy.chart.json
    normal.chart.json
    hard.chart.json
    expert.chart.json        # optional
  analysis/
    report.json
    onsets.json              # optional debug/intermediate
    preview.png              # optional chart density preview
  integration/
    README.md                # how to import this bundle into user's game
```

Optional targets can wrap that bundle:

```text
--target bundle          # portable bundle only; best product default
--target godot-addon     # bundle + Godot runtime/import helper
--target godot-project   # standalone playable preview project; dev/demo only
--target web-preview     # browser preview; useful for QA
--target unity-package   # future
```

## User-Facing Flow

```text
1. Upload audio
2. Choose difficulty or multiple difficulties
3. Choose output target
4. Generate
5. Download/import output
```

Recommended UI fields:

```text
Audio: song.mp3 / wav / m4a / flac
Difficulties: Easy / Normal / Hard / Expert / Custom
Output: Bundle / Godot Addon / Godot Preview Project / Web Preview
Theme tags: cooking / generic / custom lane names
Lane count: 3 by default, or explicit
Keys: A/S/D by default, or explicit
Advanced: note density, min gap, speed, judgement windows, allow holds/doubles
```

## Difficulty Must Be a First-Class Parameter

Difficulty is not an afterthought. It controls chart generation and runtime feel.

### Preset Table

| Difficulty | Lanes | Notes / 30s | Min gap | Note speed | Perfect | Good | Doubles | Holds |
|---|---:|---:|---:|---:|---:|---:|---|---|
| easy | 3 | 30-50 | 0.38-0.45s | 360 | 0.080s | 0.160s | no | no |
| normal | 3 | 55-90 | 0.24-0.32s | 520 | 0.060s | 0.120s | rare | optional |
| hard | 3 | 90-140 | 0.14-0.22s | 650 | 0.045s | 0.090s | yes | yes |
| expert | 3 | 130-220 | 0.08-0.14s | 780 | 0.035s | 0.070s | yes | yes |

The actual note cap should scale by song duration:

```text
max_notes = notes_per_30s[difficulty] * duration_seconds / 30
```

### CLI Shape

Generate one difficulty:

```bash
python scripts/create_rhythm_bundle.py input.mp3 \
  --difficulty normal \
  --lanes 3 \
  --keys A,S,D \
  --target bundle \
  --out dist/input_bundle
```

Generate multiple difficulties:

```bash
python scripts/create_rhythm_bundle.py input.mp3 \
  --difficulties easy,normal,hard \
  --lanes 3 \
  --keys A,S,D \
  --target bundle \
  --out dist/input_bundle
```

Custom difficulty:

```bash
python scripts/create_rhythm_bundle.py input.mp3 \
  --difficulty custom \
  --lanes 3 \
  --keys A,S,D \
  --note-density 1.8 \
  --min-gap 0.28 \
  --note-speed 480 \
  --good-window 0.13 \
  --out dist/input_bundle
```

## Chart JSON Contract

Each chart file should be engine-neutral and self-contained except for audio path references.

```json
{
  "schema": "com.rhythmkit.chart.v1",
  "song_id": "never_gonna_give_you_up",
  "title": "Never Gonna Give You Up",
  "audio": "../audio/song.wav",
  "duration": 29.9755,
  "bpm": 112.35,
  "difficulty": {
    "name": "normal",
    "rating": 4,
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
    {"id": 1, "time": 0.7663, "lane": 0, "type": "tap", "source": "onset", "confidence": 0.82},
    {"id": 2, "time": 1.3003, "lane": 1, "type": "tap", "source": "beat", "confidence": 0.74}
  ]
}
```

Important rules:

- `time` is seconds from audio start after offset correction.
- Lanes are integer indices; games can render them however they want.
- Difficulty/rendering parameters live in `difficulty`, so host games can choose to respect or override them.
- Do not bake Godot/Unity node names into the chart.

## metadata.json Contract

```json
{
  "schema": "com.rhythmkit.bundle.v1",
  "song_id": "never_gonna_give_you_up",
  "title": "Never Gonna Give You Up",
  "artist": "Rick Astley",
  "audio": "audio/song.wav",
  "duration": 29.9755,
  "bpm": 112.35,
  "charts": {
    "easy": "charts/easy.chart.json",
    "normal": "charts/normal.chart.json",
    "hard": "charts/hard.chart.json"
  },
  "generated_by": "audio-to-rhythm-godot-kit",
  "generator_version": "0.2.0"
}
```

## Godot Integration Design

The product should give Godot users two options.

### Option A: Import the portable bundle into their own renderer

Tell the user:

1. Copy the bundle into their Godot project:

```text
res://levels/never_gonna_give_you_up/
  metadata.json
  audio/song.wav
  charts/normal.chart.json
```

2. Load `metadata.json`.
3. Let the player select a chart difficulty.
4. Load the selected chart JSON.
5. Play the audio with `AudioStreamPlayer`.
6. Spawn/render notes according to `note.time`, `note.lane`, and `note.type`.

Minimal GDScript loader pattern:

```gdscript
var metadata = JSON.parse_string(FileAccess.get_file_as_string("res://levels/song/metadata.json"))
var chart_path = "res://levels/song/" + metadata["charts"]["normal"]
var chart = JSON.parse_string(FileAccess.get_file_as_string(chart_path))
var audio = AudioStreamWAV.load_from_file("res://levels/song/" + metadata["audio"])
$AudioStreamPlayer.stream = audio
$AudioStreamPlayer.play()
```

### Option B: Use provided Godot runtime addon

The generator can also ship a reusable Godot addon:

```text
addons/rhythmkit/
  RhythmLevelLoader.gd
  RhythmChart.gd
  RhythmPlayer.gd
  RhythmGameView.tscn
  README.md
```

Then users import a bundle and instantiate:

```gdscript
var player = preload("res://addons/rhythmkit/RhythmPlayer.gd").new()
add_child(player)
player.load_bundle("res://levels/never_gonna_give_you_up", "normal")
player.start()
```

This is the clean product path: the converter outputs bundles; the addon teaches/helps users consume them.

## Output Modes

### 1. Bundle mode: default product mode

Best for real users and arbitrary games.

```bash
create_rhythm_bundle.py song.mp3 --difficulties easy,normal,hard --lanes 3 --keys A,S,D --target bundle
```

Output: portable level bundle only.

### 2. Godot addon mode

Best for Godot developers who want a ready runtime.

```bash
create_rhythm_bundle.py song.mp3 --difficulties easy,normal,hard --lanes 3 --keys A,S,D --target godot-addon
```

Output:

```text
output/
  addons/rhythmkit/...
  levels/song/...
```

### 3. Godot project mode

Best for demos, QA, and agent verification. Not the main product output.

```bash
create_rhythm_bundle.py song.mp3 --difficulty normal --lanes 3 --keys A,S,D --target godot-project
```

Output: standalone playable project with the bundle embedded.

### 4. Web preview mode

Best for fast chart QA before engine import.

```bash
create_rhythm_bundle.py song.mp3 --difficulty normal --target web-preview
```

Output: browser-playable preview.

## Engine-Agnostic Runtime Algorithm

Any game can consume the output with this logic:

```text
load metadata.json
load selected chart.json
load audio file
start audio
while playing:
  now = audio_playback_time - chart.offset
  for each unspawned note where note.time - now <= spawn_ahead:
    spawn visual note in note.lane
  on player input lane:
    find nearest unhit note in lane
    delta = abs(note.time - now)
    if delta <= perfect_window: Perfect
    elif delta <= good_window: Good
    else: Miss
```

This should be documented for users of Godot, Unity, Unreal, Cocos, web canvas, or custom engines.

## Implementation Roadmap

### Phase 1: Convert current project from “Godot preview generator” to “bundle generator”

Create:

```text
scripts/create_rhythm_bundle.py
scripts/difficulty_presets.py
scripts/write_bundle.py
```

Keep current Godot preview as:

```text
scripts/export_godot_project.py
```

### Phase 2: Multi-difficulty generation

Support:

```text
--difficulty normal
--difficulties easy,normal,hard
--difficulty-config custom.json
```

Generate one shared audio file and multiple chart files.

### Phase 3: Godot runtime addon

Create:

```text
templates/godot_addon/addons/rhythmkit/
```

The addon loads any bundle and renders a default playable view.

### Phase 4: User integration docs

Generate `integration/README.md` inside every bundle with:

- what files mean;
- how to choose difficulty;
- Godot import steps;
- custom engine pseudocode;
- known limitations.

### Phase 5: Optional Web preview

Add `--target web-preview` for fast QA.

## Product Summary

Correct product mental model:

```text
The converter does not own the final gameplay.
It produces standardized rhythm level data + audio + optional adapters.
The host game owns visuals, scoring flavor, progression, UI, and theme.
```

So the default output should be:

```text
level_bundle.zip
```

The Godot project should be a preview/import example, not the main artifact.
