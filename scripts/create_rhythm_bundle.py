#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_audio import DEFAULT_KEYS, validate_layout  # noqa: E402
from difficulty_presets import list_presets, resolve_presets_from_args, with_lane_count  # noqa: E402
from write_bundle import create_bundle, slugify, write_godot_addon, write_json, write_project_godot, write_text, zip_directory  # noqa: E402


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Create a portable rhythm-game level bundle from an uploaded audio file")
    ap.add_argument("audio", help="Input audio file: mp3/wav/m4a/flac/ogg/etc. Any ffmpeg-supported format.")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--target", choices=["bundle", "godot-addon", "godot-project"], default="bundle")
    ap.add_argument("--difficulty", default=None, help="Single difficulty: easy/normal/hard/expert/custom")
    ap.add_argument("--difficulties", default=None, help="Comma-separated difficulties, e.g. easy,normal,hard")
    ap.add_argument("--theme", default="cooking", choices=["cooking", "generic"])
    ap.add_argument("--title", default=None)
    ap.add_argument("--artist", default=None)
    ap.add_argument("--song-id", default=None)
    ap.add_argument("--zip", action="store_true", help="Also create <out>.zip")
    ap.add_argument("--no-original", action="store_true", help="Do not copy original uploaded audio into audio/original.<ext>")

    # Layout knobs apply to every generated difficulty. Current product default is 3-key A/S/D.
    ap.add_argument("--lanes", type=int, default=3, help="Fixed product layout: 3 lanes")
    ap.add_argument("--keys", default=",".join(DEFAULT_KEYS), help="Fixed product keys: A,S,D")

    # Custom difficulty knobs. Density/timing are only used when --difficulty custom or --difficulties includes custom.
    ap.add_argument("--note-density", type=float, default=2.0, help="Custom difficulty density in notes per second")
    ap.add_argument("--min-gap", type=float, default=0.25)
    ap.add_argument("--note-speed", type=float, default=520.0)
    ap.add_argument("--perfect-window", type=float, default=0.060)
    ap.add_argument("--good-window", type=float, default=0.120)
    ap.add_argument("--rating", type=int, default=5)
    ap.add_argument("--allow-doubles", action="store_true")
    ap.add_argument("--allow-holds", action="store_true")
    return ap.parse_args()


def write_target_readme(root: Path, *, song_id: str, target: str, difficulties: list[str]) -> None:
    diff_list = ", ".join(difficulties)
    if target == "bundle":
        return
    write_text(
        root / "README_GODOT_IMPORT.md",
        f"""# Godot Rhythm Bundle Package

This output contains a portable level bundle plus a minimal Godot runtime addon. It is designed for **AI-assisted import** into a user's own Godot game.

## Contents

```text
addons/rhythmkit/          # reusable Godot loader/player, usually installed once
levels/{song_id}/          # generated rhythm level bundle for this song
project.godot              # preview project entry point
```

Difficulties: `{diff_list}`

## Preview first

Open this folder as a Godot 4 project and run it. The default scene is:

```text
res://addons/rhythmkit/RhythmGameView.tscn
```

## AI-first import into an existing Godot project

Give Codex / Claude Code / Cursor / Hermes access to the user's Godot project, then paste this generated prompt:

```text
levels/{song_id}/integration/AI_GODOT_IMPORT_PROMPT.md
```

Tell the AI where the rhythm level should enter the game: main menu, level select, NPC, map trigger, or debug/test entry.

The AI should copy these directories into the target project:

```text
addons/rhythmkit/          # reusable runtime
levels/{song_id}/          # this song's bundle
```

Then wire the chosen game entry point to:

```gdscript
var view = preload("res://addons/rhythmkit/RhythmGameView.tscn").instantiate()
add_child(view)
view.load_bundle("res://levels/{song_id}", "normal")
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
""",
    )


def main() -> int:
    args = parse_args()
    audio = Path(args.audio).resolve()
    if not audio.exists():
        raise FileNotFoundError(audio)
    presets = [with_lane_count(p, args.lanes) for p in resolve_presets_from_args(args)]
    key_names = validate_layout(args.lanes, args.keys)
    title = args.title or audio.stem
    song_id = args.song_id or slugify(title)
    out = Path(args.out).resolve()

    if args.target == "bundle":
        bundle_dir = out
        result = create_bundle(
            audio_path=audio,
            out_dir=bundle_dir,
            presets=presets,
            title=title,
            artist=args.artist,
            song_id=song_id,
            theme=args.theme,
            keys=key_names,
            include_original=not args.no_original,
        )
        target_info = {"target": "bundle", "bundle_dir": str(bundle_dir)}
    else:
        root = out
        bundle_dir = root / "levels" / song_id
        result = create_bundle(
            audio_path=audio,
            out_dir=bundle_dir,
            presets=presets,
            title=title,
            artist=args.artist,
            song_id=song_id,
            theme=args.theme,
            keys=key_names,
            include_original=not args.no_original,
        )
        default_difficulty = presets[0].name
        if any(p.name == "normal" for p in presets):
            default_difficulty = "normal"
        write_godot_addon(root, default_song_id=song_id, default_difficulty=default_difficulty)
        write_project_godot(root, f"{song_id}_rhythm_preview", "res://addons/rhythmkit/RhythmGameView.tscn")
        write_target_readme(root, song_id=song_id, target=args.target, difficulties=[p.name for p in presets])
        target_info = {
            "target": args.target,
            "project_godot": str(root / "project.godot"),
            "bundle_dir": str(bundle_dir),
            "addon_dir": str(root / "addons" / "rhythmkit"),
            "default_difficulty": default_difficulty,
        }

    zip_path = None
    if args.zip:
        zip_root = out if args.target == "bundle" else out
        zip_path = zip_directory(zip_root)

    summary = {
        "ok": True,
        "song_id": song_id,
        "title": title,
        "difficulties": [p.name for p in presets],
        "metadata": result["metadata"],
        "layout": {"lanes": args.lanes, "keys": key_names},
        "target": target_info,
        "zip": zip_path,
    }
    # A top-level manifest is useful for automation even in target wrappers.
    manifest_path = (out / "generation_manifest.json") if args.target != "bundle" else (out / "generation_manifest.json")
    write_json(manifest_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
