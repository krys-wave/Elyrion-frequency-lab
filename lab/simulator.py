from datetime import datetime, timedelta, timezone
import numpy as np
from .schema import CHANNELS, Frame


class Simulator:
    """Seeded simulation; audio and scalar clocks share an acquisition timebase."""
    def __init__(self, room="Room A", run_id="preview", seed=1, rate=20, start=None):
        self.room, self.run_id, self.rate = room, run_id, rate
        self.rng = np.random.default_rng(seed)
        self.start = start or datetime.now(timezone.utc)
        self.index = 0
        self.audio_rate = 8000
        self.tone_phase = 0.

    def frame(self, disturbance=0.0, tone=None):
        t = self.index / self.rate
        f = 1.25 if self.room == "Room A" else 2.0
        wave = np.sin(2 * np.pi * f * t + np.arange(9) * .2)
        base = np.array([24e-6, 4e-6, 39e-6, 0., 0., 9.80665, 0., 0., 0.])
        scale = np.array([2e-6] * 3 + [.03] * 3 + [.004] * 3)
        motion = base + scale * (wave + self.rng.normal(0, .06, 9) + disturbance)
        env = [295.15 + .2 * np.sin(t / 120) + (self.room == "Room B"), .45 + .005 * np.sin(t / 180), 101325 + 8 * np.sin(t / 90)]
        at = t + np.arange(self.audio_rate // self.rate) / self.audio_rate
        audio = .01 * np.sin(2 * np.pi * (160 if self.room == "Room A" else 240) * at)
        audio += self.rng.normal(0, .001, len(at))
        if tone:
            phase = self.tone_phase + 2 * np.pi * tone[0] * np.arange(len(at)) / self.audio_rate
            audio += tone[1] * np.sin(phase)
            self.tone_phase = float((self.tone_phase + 2 * np.pi * tone[0] * len(at) / self.audio_rate) % (2 * np.pi))
        frame = Frame(timestamp=self.start + timedelta(seconds=t), device_id="Sensor Node 01 (simulated)", firmware_version="sim-0.1", sampling_rate=self.rate, acoustic_sampling_rate=self.audio_rate, calibration={"status": "synthetic", "seeded": True}, run_id=self.run_id, location_id=self.room, source="simulation", values=dict(zip(CHANNELS, [*motion, *env])), acoustic_samples=audio.tolist())
        self.index += 1
        return frame
