# Godot Rhythm Bundle Package

This output contains a portable level bundle plus a minimal Godot runtime addon. It is designed for **AI-assisted import** into a user's own Godot game.

## Contents

```text
addons/rhythmkit/          # reusable Godot loader/player, usually installed once
levels/ready_expert_demo/          # generated rhythm level bundle for this song
project.godot              # preview project entry point
```

Difficulties: `expert`

## Preview first

Open this folder as a Godot 4 project and run it. The default scene is:

```text
res://scenes/RhythmKitPreview.tscn
```

## AI-first import into an existing Godot project

Give Codex / Claude Code / Cursor / Hermes access to the user's Godot project, then paste this generated prompt:

```text
levels/ready_expert_demo/integration/AI_GODOT_IMPORT_PROMPT.md
```

Tell the AI where the rhythm level should enter the game: main menu, level select, NPC, map trigger, or debug/test entry.

The AI should copy these directories into the target project:

```text
addons/rhythmkit/          # reusable runtime
levels/ready_expert_demo/          # this song's bundle
```

Then wire the chosen game entry point to:

```gdscript
var view = preload("res://addons/rhythmkit/RhythmGameView.tscn").instantiate()
add_child(view)
view.load_bundle("res://levels/ready_expert_demo", "expert")
view.start_game()
```

## Adding more music later

After `addons/rhythmkit/` is installed once, a new song is just a new bundle:

```text
levels/<new_song_id>/
```

Future workflow for the AI:

```text
1. Take a new audio file from the user.
2. Generate a bundle with audio-to-rhythm-godot-kit.
3. Copy it to res://levels/<new_song_id>/.
4. Update the same menu/level-select/trigger list.
5. Run Godot headless/console and fix errors.
```
