from __future__ import annotations

import math
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_rhythm_bundle.py"


def write_tiny_wav(path: Path, seconds: float = 1.0, sr: int = 44100) -> None:
    frames = int(seconds * sr)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        data = bytearray()
        for i in range(frames):
            sample = int(0.35 * 32767 * math.sin(2.0 * math.pi * 440.0 * i / sr))
            data += sample.to_bytes(2, "little", signed=True)
        w.writeframes(bytes(data))


class GodotPreviewExportTests(unittest.TestCase):
    def test_godot_addon_target_runs_preview_scene_with_generated_bundle_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            audio = tmp_path / "mini.wav"
            out = tmp_path / "out"
            write_tiny_wav(audio)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(audio),
                    "--target",
                    "godot-addon",
                    "--difficulty",
                    "expert",
                    "--title",
                    "Mini Preview",
                    "--song-id",
                    "mini_preview",
                    "--out",
                    str(out),
                ],
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr + result.stdout)

            project = (out / "project.godot").read_text(encoding="utf-8")
            preview_scene = out / "scenes" / "RhythmKitPreview.tscn"
            runtime_scene = out / "addons" / "rhythmkit" / "RhythmGameView.tscn"
            self.assertIn('run/main_scene="res://scenes/RhythmKitPreview.tscn"', project)
            self.assertTrue(preview_scene.exists(), "preview scene should be generated for direct Godot runs")
            self.assertTrue(runtime_scene.exists(), "runtime scene should exist")

            scene_text = preview_scene.read_text(encoding="utf-8")
            self.assertIn('instance=ExtResource("1")', scene_text)
            self.assertIn('bundle_path = "res://levels/mini_preview"', scene_text)
            self.assertIn('difficulty = "expert"', scene_text)
            self.assertIn('auto_start = true', scene_text)

            runtime_text = runtime_scene.read_text(encoding="utf-8")
            self.assertIn('bundle_path = "res://levels/mini_preview"', runtime_text)
            self.assertIn('difficulty = "expert"', runtime_text)
            self.assertIn('auto_start = true', runtime_text)


if __name__ == "__main__":
    unittest.main()
