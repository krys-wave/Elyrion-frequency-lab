from datetime import datetime, timezone
import json
import numpy as np
import pytest
from lab.engine import compare, frequency_map, persistent_invariant, spectrum, state
from lab.schema import Frame
from lab.simulator import Simulator


def frames(room="Room A", seed=1, count=200):
    sim = Simulator(room, seed=seed, start=datetime(2026, 1, 1, tzinfo=timezone.utc))
    return [sim.frame() for _ in range(count)]


def test_fft_amplitude_phase_and_psd():
    rate = 100
    t = np.arange(1000) / rate
    result = spectrum(2 * np.cos(2 * np.pi * 5 * t + .4), rate)
    assert result["frequency_hz"] == pytest.approx(5)
    assert result["amplitude"] == pytest.approx(2, rel=.01)
    assert result["phase_rad"] == pytest.approx(.4, abs=.01)
    assert result["frequencies_hz"][np.argmax(result["psd"])] == pytest.approx(5, abs=.2)


def test_reproducibility_and_room_discrimination():
    a = frequency_map(frames())
    again = frequency_map(frames())
    b = frequency_map(frames("Room B"))
    assert json.dumps(a, sort_keys=True) == json.dumps(again, sort_keys=True)
    assert compare(a, again)["similarity"] == 1
    assert compare(a, b)["similarity"] < .8
    assert compare(a, b)["dominant_features"]
    assert a["relationships"][0]["coherence"] > .9
    assert abs(a["relationships"][0]["phase_difference_rad"]) == pytest.approx(.2, abs=.1)


def test_pi_requires_repeated_qualifying_runs():
    maps = [frequency_map(frames(seed=i)) for i in range(3)]
    assert persistent_invariant(maps[:2])["status"] == "Insufficient runs for PI"
    pi = persistent_invariant(maps)
    assert pi["qualifying_runs"] == 3
    assert pi["confidence"] > .8
    assert len(state(maps[0], pi)["dynamic"]) == len(maps[0]["feature_vector"])
    assert state(maps[0], pi) == state(maps[0], pi)
    assert state(maps[0], {})["status"] == "PA preliminary"


def test_insufficient_and_irregular_input_do_not_invent_results():
    assert frequency_map(frames(count=20))["status"] == "Collecting baseline"
    data = frames()
    data.pop(10)
    assert "Irregular" in frequency_map(data)["status"]


def test_silent_channels_are_json_safe():
    data = frames()
    for f in data:
        f.values = {k: 0. for k in f.values}
        f.acoustic_samples = [0.] * len(f.acoustic_samples)
    result = frequency_map(data)
    json.dumps(result, allow_nan=False)
    assert result["relationships"][0]["coupling"] is None
    assert result["components"]["M_X"]["status"] == "no oscillatory signal"
    assert result["components"]["M_X"]["phase_rad"] is None
    assert compare(result, result)["status"] == "ready"


def test_schema_rejects_nonfinite_or_missing_data():
    raw = frames(count=1)[0].model_dump(mode="json")
    raw["values"]["M_X"] = float("nan")
    with pytest.raises(ValueError): Frame.model_validate(raw)
    raw["values"].pop("M_X")
    with pytest.raises(ValueError): Frame.model_validate(raw)


def test_synthetic_acoustic_response_changes_features():
    sim = Simulator()
    pre = frequency_map([sim.frame() for _ in range(100)])
    mid = frequency_map([sim.frame(tone=(440, .1)) for _ in range(100)])
    assert mid["acoustic"]["rms"] > pre["acoustic"]["rms"] * 5
    assert compare(mid, pre)["anomaly_score"] > 1
