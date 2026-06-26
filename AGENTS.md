# audio-to-rhythm-godot-kit

Goal: turn an uploaded audio file into a portable rhythm-game level bundle, with optional Godot preview/import outputs.

## Primary command: bundle-first

```bash
python scripts/create_rhythm_bundle.py path/to/song.mp3 \
  --difficulties easy,normal,hard \
  --lanes 3 \
  --keys A,S,D \
  --target bundle \
  --out dist/song_bundle
```

Default product output:

```text
dist/song_bundle/
  metadata.json
  audio/song.wav
  audio/original.<ext>
  charts/easy.chart.json
  charts/normal.chart.json
  charts/hard.chart.json
  analysis/report.json
  integration/README.md
  integration/AI_GODOT_IMPORT_PROMPT.md
```

## Optional targets

Godot addon/import package:

```bash
python scripts/create_rhythm_bundle.py path/to/song.mp3 \
  --difficulties easy,normal,hard \
  --lanes 3 \
  --keys A,S,D \
  --target godot-addon \
  --out dist/song_godot_addon
```

Standalone Godot preview project:

```bash
python scripts/create_rhythm_bundle.py path/to/song.mp3 \
  --difficulty normal \
  --lanes 3 \
  --keys A,S,D \
  --target godot-project \
  --out dist/song_preview_project
```

Legacy direct preview still exists:

```bash
python scripts/create_rhythm_game.py path/to/song.mp3 --theme cooking --lanes 3 --keys A,S,D --out dist/song_godot
```

## Development rules for agents

- Treat `metadata.json + charts/*.chart.json + audio/song.wav` as the core product contract.
- Godot preview projects are demos/verification artifacts, not the main product output.
- Difficulty is a first-class parameter. Use `scripts/difficulty_presets.py`; do not hard-code one difficulty.
- Do not bake game-specific art into the chart. Host games own visuals/UI/scoring flavor.
- Every bundle must include `integration/AI_GODOT_IMPORT_PROMPT.md` so users can hand integration to an AI coding agent.
- Prefer optional dependencies. MVP must work with Python + numpy + ffmpeg only.
- Verify generated Godot projects/addons with the local Godot console binary if available.
- Keep chart schema engine-neutral. Godot/Unity/Web consume the same JSON.

## Current MVP

- Audio analysis: ffmpeg decode -> numpy energy/spectral-flux onset detection -> BPM estimate -> chart notes.
- Multi-difficulty generation: easy/normal/hard/expert/custom presets.
- Bundle writer: portable audio + metadata + charts + integration docs.
- Godot addon: `addons/rhythmkit` loader/player that can be copied into a user's project.
- Godot project preview: standalone player for quick QA.
- Theme: `cooking` maps the default 3-key layout to CUT/STIR/FIRE on A/S/D.
