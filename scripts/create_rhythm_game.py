#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_audio import generate_chart  # noqa: E402
from export_godot import export_godot_project  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a playable Godot rhythm-game prototype from an audio file")
    ap.add_argument("audio", help="Input audio file, any ffmpeg-supported format")
    ap.add_argument("--out", required=True, help="Output Godot project directory")
    ap.add_argument("--theme", default="cooking", choices=["cooking", "generic"])
    ap.add_argument("--lanes", type=int, default=4)
    ap.add_argument("--title", default=None)
    ap.add_argument("--max-notes", type=int, default=260)
    ap.add_argument("--min-gap", type=float, default=0.15)
    args = ap.parse_args()

    audio = Path(args.audio).resolve()
    out = Path(args.out).resolve()
    build_dir = out / ".build"
    build_dir.mkdir(parents=True, exist_ok=True)

    chart, report = generate_chart(
        audio,
        title=args.title or audio.stem,
        theme=args.theme,
        lanes=args.lanes,
        max_notes=args.max_notes,
        min_gap_s=args.min_gap,
    )
    raw_chart_path = build_dir / "chart.raw.json"
    raw_report_path = build_dir / "analysis_report.json"
    raw_chart_path.write_text(json.dumps(chart, ensure_ascii=False, indent=2), encoding="utf-8")
    raw_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = export_godot_project(raw_chart_path, audio, out, project_name=f"{audio.stem}_rhythm")
    final_report = {
        "analysis": report,
        "export": manifest,
        "command": {
            "audio": str(audio),
            "out": str(out),
            "theme": args.theme,
            "lanes": args.lanes,
            "max_notes": args.max_notes,
            "min_gap": args.min_gap,
        },
    }
    (out / "report.json").write_text(json.dumps(final_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(final_report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
