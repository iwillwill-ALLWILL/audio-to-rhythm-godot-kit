from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from analyze_audio import apply_playability_modifiers, select_peaks_by_dynamic_density  # noqa: E402
from difficulty_presets import PRESETS  # noqa: E402


class ChartFeelTests(unittest.TestCase):
    def test_dynamic_density_keeps_more_notes_in_high_energy_sections(self) -> None:
        times = np.arange(0.0, 16.0, 0.5, dtype=np.float32)
        peaks = list(range(len(times)))
        env = np.full(len(times), 0.25, dtype=np.float32)
        env[(times >= 8.0) & (times < 12.0)] = 1.0

        selected = select_peaks_by_dynamic_density(
            peaks,
            env,
            times,
            max_notes=12,
            section_seconds=4.0,
            dynamic_density=0.85,
        )

        selected_times = [float(times[i]) for i in selected]
        high_energy_count = sum(8.0 <= t < 12.0 for t in selected_times)
        quiet_intro_count = sum(0.0 <= t < 4.0 for t in selected_times)

        self.assertEqual(len(selected), 12)
        self.assertGreater(high_energy_count, quiet_intro_count)
        self.assertEqual(selected, sorted(selected))

    def test_playability_modifiers_add_holds_and_doubles_without_invalid_lanes(self) -> None:
        notes = [
            {"time": round(i * 0.5, 3), "lane": i % 3, "type": "tap", "confidence": 0.95}
            for i in range(24)
        ]

        enhanced = apply_playability_modifiers(
            notes,
            lane_count=3,
            allow_doubles=True,
            allow_holds=True,
            double_rate=0.35,
            hold_rate=0.35,
            hold_min=0.35,
            hold_max=0.9,
            max_notes=32,
            min_gap_s=0.12,
        )

        self.assertTrue(any(n["type"] == "hold" and n.get("duration", 0) >= 0.35 for n in enhanced))
        self.assertTrue(any(n.get("source") == "accent_double" for n in enhanced))
        self.assertLessEqual(len(enhanced), 32)
        self.assertTrue(all(0 <= int(n["lane"]) < 3 for n in enhanced))

        by_time: dict[float, list[int]] = {}
        for note in enhanced:
            by_time.setdefault(float(note["time"]), []).append(int(note["lane"]))
        self.assertTrue(any(len(set(lanes)) >= 2 for lanes in by_time.values()))

    def test_difficulty_presets_scale_handfeel_features(self) -> None:
        self.assertEqual(PRESETS["easy"].double_rate, 0.0)
        self.assertLess(PRESETS["normal"].double_rate, PRESETS["hard"].double_rate)
        self.assertLess(PRESETS["hard"].double_rate, PRESETS["expert"].double_rate)
        self.assertLess(PRESETS["normal"].hold_rate, PRESETS["expert"].hold_rate)
        self.assertLess(PRESETS["easy"].dynamic_density, PRESETS["expert"].dynamic_density)


if __name__ == "__main__":
    unittest.main()
