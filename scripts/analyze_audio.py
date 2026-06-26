#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_SR = 22050
DEFAULT_LANES = 3
DEFAULT_KEYS = ["A", "S", "D"]
THEME_LANES = {
    "cooking": ["CUT", "STIR", "FIRE"],
    "generic": ["LANE 1", "LANE 2", "LANE 3"],
}


def parse_key_names(raw: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if raw is None:
        return list(DEFAULT_KEYS)
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return list(DEFAULT_KEYS)
        if "," in text:
            keys = [part.strip().upper() for part in text.split(",") if part.strip()]
        else:
            keys = [ch.upper() for ch in text if not ch.isspace()]
    else:
        keys = [str(part).strip().upper() for part in raw if str(part).strip()]
    return keys or list(DEFAULT_KEYS)


def validate_layout(lanes: int, keys: str | list[str] | tuple[str, ...] | None = None) -> list[str]:
    key_names = parse_key_names(keys)
    if lanes != DEFAULT_LANES:
        raise ValueError(f"This kit is fixed to {DEFAULT_LANES} lanes for the A/S/D product layout; got {lanes}")
    if key_names != DEFAULT_KEYS:
        raise ValueError(f"This kit is fixed to keys {','.join(DEFAULT_KEYS)}; got {','.join(key_names)}")
    return key_names


def find_ffmpeg() -> str:
    env = os.environ.get("FFMPEG") or os.environ.get("FFMPEG_PATH")
    if env and Path(env).exists():
        return env
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    raise RuntimeError("ffmpeg not found on PATH. Install ffmpeg or set FFMPEG/FFMPEG_PATH.")


def find_ffmpeg_optional() -> str | None:
    try:
        return find_ffmpeg()
    except RuntimeError:
        return None


def decode_pcm_wav(path: str | Path, sr: int = DEFAULT_SR) -> tuple[np.ndarray, int]:
    """Decode an uncompressed PCM WAV with the Python stdlib.

    This lets WAV-only demo/test flows work even on machines without ffmpeg. Arbitrary
    uploaded formats still require ffmpeg.
    """
    with wave.open(str(path), "rb") as w:
        channels = w.getnchannels()
        source_sr = w.getframerate()
        sampwidth = w.getsampwidth()
        frames = w.readframes(w.getnframes())

    if sampwidth == 1:
        audio = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sampwidth == 2:
        audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif sampwidth == 4:
        audio = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise RuntimeError(f"unsupported WAV sample width without ffmpeg: {sampwidth} bytes")

    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if source_sr != sr and audio.size:
        old_x = np.linspace(0.0, 1.0, audio.size, endpoint=False, dtype=np.float32)
        new_len = max(1, int(round(audio.size * sr / source_sr)))
        new_x = np.linspace(0.0, 1.0, new_len, endpoint=False, dtype=np.float32)
        audio = np.interp(new_x, old_x, audio).astype(np.float32)
    audio = np.nan_to_num(audio.astype(np.float32), copy=False)
    return audio, sr


def decode_audio(path: str | Path, sr: int = DEFAULT_SR) -> tuple[np.ndarray, int]:
    """Decode any ffmpeg-supported audio file into mono float32 numpy array."""
    path_obj = Path(path)
    wav_error: Exception | None = None
    if path_obj.suffix.lower() == ".wav":
        try:
            return decode_pcm_wav(path_obj, sr=sr)
        except Exception as exc:
            wav_error = exc

    ffmpeg = find_ffmpeg_optional()
    if ffmpeg is None:
        if wav_error is not None:
            raise RuntimeError(f"ffmpeg not found and WAV fallback failed: {wav_error}") from wav_error
        raise RuntimeError("ffmpeg not found on PATH. Install ffmpeg or set FFMPEG/FFMPEG_PATH.")
    path = str(path_obj)
    cmd = [
        ffmpeg,
        "-v",
        "error",
        "-i",
        path,
        "-ac",
        "1",
        "-ar",
        str(sr),
        "-f",
        "f32le",
        "-",
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed: {p.stderr.decode('utf-8', 'ignore')}")
    audio = np.frombuffer(p.stdout, dtype=np.float32).copy()
    if audio.size == 0:
        raise RuntimeError("decoded audio is empty")
    audio = np.nan_to_num(audio, copy=False)
    max_abs = float(np.max(np.abs(audio)))
    if max_abs > 1.0:
        audio = audio / max_abs
    return audio, sr


def frame_audio(audio: np.ndarray, frame_size: int, hop: int) -> np.ndarray:
    if len(audio) < frame_size:
        padded = np.zeros(frame_size, dtype=np.float32)
        padded[: len(audio)] = audio
        audio = padded
    n = 1 + (len(audio) - frame_size) // hop
    shape = (n, frame_size)
    strides = (audio.strides[0] * hop, audio.strides[0])
    return np.lib.stride_tricks.as_strided(audio, shape=shape, strides=strides)


def normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    lo = float(np.min(x)) if x.size else 0.0
    hi = float(np.max(x)) if x.size else 0.0
    if hi - lo < 1e-9:
        return np.zeros_like(x, dtype=np.float32)
    return (x - lo) / (hi - lo)


def moving_average(x: np.ndarray, width: int = 5) -> np.ndarray:
    if width <= 1 or x.size < width:
        return x
    kernel = np.ones(width, dtype=np.float32) / width
    return np.convolve(x, kernel, mode="same")


def extract_features(audio: np.ndarray, sr: int, frame_size: int = 1024, hop: int = 512) -> dict[str, Any]:
    frames = frame_audio(audio, frame_size, hop).copy()
    window = np.hanning(frame_size).astype(np.float32)
    frames_win = frames * window[None, :]

    energy = np.mean(frames * frames, axis=1)
    energy_db = 10.0 * np.log10(energy + 1e-10)
    energy_rise = np.maximum(0.0, np.diff(energy_db, prepend=energy_db[0]))

    mags = np.abs(np.fft.rfft(frames_win, axis=1))
    flux = np.maximum(0.0, np.diff(mags, axis=0, prepend=mags[:1])).sum(axis=1)

    freqs = np.fft.rfftfreq(frame_size, 1.0 / sr)
    mag_sum = mags.sum(axis=1) + 1e-9
    centroid = (mags * freqs[None, :]).sum(axis=1) / mag_sum

    env = normalize(flux) * 0.75 + normalize(energy_rise) * 0.25
    env = moving_average(env, 3)
    times = np.arange(env.size, dtype=np.float32) * hop / sr
    return {
        "times": times,
        "onset_env": env,
        "energy": energy,
        "centroid": centroid,
        "frame_size": frame_size,
        "hop": hop,
    }


def pick_peaks(env: np.ndarray, sr: int, hop: int, min_gap_s: float = 0.16) -> list[int]:
    if env.size < 3:
        return []
    med = float(np.median(env))
    std = float(np.std(env))
    threshold = max(0.08, med + std * 0.55)
    min_gap = max(1, int(round(min_gap_s * sr / hop)))
    candidates: list[tuple[float, int]] = []
    for i in range(1, env.size - 1):
        if env[i] >= threshold and env[i] >= env[i - 1] and env[i] >= env[i + 1]:
            candidates.append((float(env[i]), i))
    # Greedy non-max suppression by confidence.
    selected: list[int] = []
    for _, idx in sorted(candidates, reverse=True):
        if all(abs(idx - j) >= min_gap for j in selected):
            selected.append(idx)
    return sorted(selected)


def estimate_bpm(env: np.ndarray, sr: int, hop: int, min_bpm: float = 70.0, max_bpm: float = 180.0) -> float:
    if env.size < 8:
        return 120.0
    x = env.astype(np.float32)
    x = x - float(np.mean(x))
    if float(np.max(np.abs(x))) < 1e-6:
        return 120.0
    fps = sr / hop
    min_lag = max(1, int(round(fps * 60.0 / max_bpm)))
    max_lag = min(len(x) - 1, int(round(fps * 60.0 / min_bpm)))
    if max_lag <= min_lag:
        return 120.0
    scores = []
    for lag in range(min_lag, max_lag + 1):
        a = x[:-lag]
        b = x[lag:]
        scores.append(float(np.dot(a, b)))
    best_lag = min_lag + int(np.argmax(scores))
    bpm = 60.0 * fps / best_lag
    while bpm < 80:
        bpm *= 2.0
    while bpm > 190:
        bpm *= 0.5
    return round(float(bpm), 2)


def lane_from_centroid(centroid_hz: float, lane_count: int, fallback_index: int) -> int:
    """Map an onset to a lane.

    Pure centroid mapping collapses finished pop/metal mixes into one high-frequency lane
    because cymbals/vocals dominate the spectrum. For gameplay, use a stable musical
    pattern and let centroid only rotate the pattern slightly.
    """
    if lane_count <= 1:
        return 0
    if lane_count == 2:
        pattern = [0, 1, 0, 1]
    elif lane_count == 3:
        pattern = [0, 1, 2, 1]
    elif lane_count == 4:
        pattern = [0, 1, 2, 3, 2, 1]
    else:
        pattern = list(range(lane_count)) + list(range(lane_count - 2, 0, -1))

    if centroid_hz < 450:
        rotation = lane_count - 1  # low hits lean right/fire
    elif centroid_hz < 1400:
        rotation = 1
    elif centroid_hz < 2600:
        rotation = 0
    else:
        rotation = 2 if lane_count > 2 else 1
    return int((pattern[fallback_index % len(pattern)] + rotation) % lane_count)


def make_lanes(theme: str, lanes: int, keys: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    names = THEME_LANES.get(theme, THEME_LANES["generic"])
    key_names = validate_layout(lanes, keys)
    out = []
    for i in range(lanes):
        out.append({"id": i, "name": names[i] if i < len(names) else f"LANE {i+1}", "key": key_names[i] if i < len(key_names) else str(i + 1)})
    return out


def generate_chart(
    audio_path: str | Path,
    *,
    title: str | None = None,
    theme: str = "cooking",
    lanes: int = 3,
    keys: list[str] | tuple[str, ...] | None = None,
    max_notes: int = 260,
    min_gap_s: float = 0.15,
    sr: int = DEFAULT_SR,
) -> tuple[dict[str, Any], dict[str, Any]]:
    keys = validate_layout(lanes, keys)
    audio, sr = decode_audio(audio_path, sr=sr)
    duration = len(audio) / sr
    features = extract_features(audio, sr)
    env = features["onset_env"]
    hop = int(features["hop"])
    peaks = pick_peaks(env, sr, hop, min_gap_s=min_gap_s)
    bpm = estimate_bpm(env, sr, hop)

    # Fallback: if audio has too few usable onsets, generate a beat grid.
    if len(peaks) < max(8, duration / 8):
        beat_interval = 60.0 / bpm
        start = 0.5
        fallback_times = np.arange(start, max(start, duration - 0.25), beat_interval)
        peaks = [min(env.size - 1, max(0, int(round(t * sr / hop)))) for t in fallback_times]

    # Density control: keep strongest peaks if too many.
    if len(peaks) > max_notes:
        ranked = sorted(peaks, key=lambda i: float(env[i]), reverse=True)[:max_notes]
        peaks = sorted(ranked)

    centroid = features["centroid"]
    times = features["times"]
    notes: list[dict[str, Any]] = []
    last_t_by_lane = [-999.0 for _ in range(lanes)]
    for seq, idx in enumerate(peaks):
        t = float(times[idx])
        if t < 0.15 or t > duration - 0.05:
            continue
        c = float(centroid[idx])
        lane = lane_from_centroid(c, lanes, seq)
        # If this lane is too dense, rotate to a nearby lane.
        if t - last_t_by_lane[lane] < min_gap_s:
            for off in range(1, lanes + 1):
                alt = (lane + off) % lanes
                if t - last_t_by_lane[alt] >= min_gap_s:
                    lane = alt
                    break
        last_t_by_lane[lane] = t
        notes.append(
            {
                "time": round(t, 4),
                "lane": int(lane),
                "type": "tap",
                "source": "onset",
                "confidence": round(float(env[idx]), 4),
                "centroid_hz": round(c, 1),
                "pitch": None,
            }
        )

    notes.sort(key=lambda n: (n["time"], n["lane"]))
    chart = {
        "version": "0.1.0",
        "title": title or Path(audio_path).stem,
        "audio": str(audio_path),
        "duration": round(duration, 4),
        "bpm": bpm,
        "offset": 0.0,
        "theme": theme,
        "lanes": make_lanes(theme, lanes, keys),
        "notes": notes,
    }
    report = {
        "audio": str(audio_path),
        "duration": round(duration, 4),
        "sample_rate": sr,
        "bpm": bpm,
        "notes": len(notes),
        "mode": "onset_mvp",
        "dependencies": {"ffmpeg": find_ffmpeg_optional(), "numpy": np.__version__},
    }
    return chart, report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze audio and generate rhythm chart JSON")
    ap.add_argument("audio")
    ap.add_argument("--chart", default="chart.json")
    ap.add_argument("--report", default="report.json")
    ap.add_argument("--theme", default="cooking")
    ap.add_argument("--lanes", type=int, default=3, help="Fixed product layout: 3 lanes")
    ap.add_argument("--keys", default=",".join(DEFAULT_KEYS), help="Fixed product keys: A,S,D")
    ap.add_argument("--max-notes", type=int, default=260)
    ap.add_argument("--min-gap", type=float, default=0.15)
    args = ap.parse_args(argv)

    chart, report = generate_chart(
        args.audio,
        theme=args.theme,
        lanes=args.lanes,
        keys=parse_key_names(args.keys),
        max_notes=args.max_notes,
        min_gap_s=args.min_gap,
    )
    Path(args.chart).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.chart).write_text(json.dumps(chart, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
