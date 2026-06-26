#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import shutil
import wave
from pathlib import Path

import numpy as np


def write_test_audio(path: str | Path, duration: float = 24.0, bpm: float = 120.0, sr: int = 44100) -> None:
    """Create a synthetic rhythm test WAV with kick/click/melody onsets."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.linspace(0, duration, int(duration * sr), endpoint=False, dtype=np.float32)
    audio = np.zeros_like(t)

    beat = 60.0 / bpm
    # Warm pad so it feels like music, not only clicks.
    audio += 0.06 * np.sin(2 * np.pi * 110 * t)
    audio += 0.04 * np.sin(2 * np.pi * 220 * t)

    melody = [523.25, 659.25, 783.99, 659.25, 587.33, 698.46, 880.0, 698.46]
    for i, start in enumerate(np.arange(0.5, duration - 0.2, beat / 2)):
        idx = int(start * sr)
        length = int(0.12 * sr)
        if idx + length > len(audio):
            break
        tt = np.arange(length, dtype=np.float32) / sr
        env = np.exp(-tt * 22.0)
        freq = melody[i % len(melody)]
        audio[idx : idx + length] += 0.35 * np.sin(2 * np.pi * freq * tt) * env
        if i % 2 == 0:
            # Low kick-like transient.
            klen = int(0.09 * sr)
            kt = np.arange(klen, dtype=np.float32) / sr
            kenv = np.exp(-kt * 45.0)
            audio[idx : idx + klen] += 0.55 * np.sin(2 * np.pi * 70 * kt) * kenv
        if i % 4 == 2:
            # High seasoning/click transient.
            clen = int(0.04 * sr)
            ct = np.arange(clen, dtype=np.float32) / sr
            cenv = np.exp(-ct * 90.0)
            audio[idx : idx + clen] += 0.25 * np.sin(2 * np.pi * 3200 * ct) * cenv

    max_abs = float(np.max(np.abs(audio))) or 1.0
    audio = audio / max_abs * 0.85
    pcm = np.int16(np.clip(audio, -1, 1) * 32767)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--duration", type=float, default=24.0)
    ap.add_argument("--bpm", type=float, default=120.0)
    args = ap.parse_args()
    write_test_audio(args.output, duration=args.duration, bpm=args.bpm)
    print(json.dumps({"output": str(Path(args.output).resolve()), "duration": args.duration, "bpm": args.bpm}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
