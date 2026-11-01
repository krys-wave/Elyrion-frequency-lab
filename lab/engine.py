"""Deterministic, versioned signal analysis and relational state descriptors."""
import hashlib
import json
import numpy as np
from scipy import signal
from .schema import CHANNELS

SCALES = np.array([2e-6] * 3 + [.03] * 3 + [.004] * 3 + [1., .01, 100.])
FEATURE_SCALES = np.r_[SCALES, SCALES, [1.] * 9, .01, 1000.]


def spectrum(x, rate):
    x = np.asarray(x, dtype=float)
    centered = x - x.mean()
    window = np.hanning(len(x))
    fft = np.fft.rfft(centered * window)
    frequencies = np.fft.rfftfreq(len(x), 1 / rate)
    amplitudes = 2 * np.abs(fft) / max(window.sum(), 1)
    peak = int(np.argmax(amplitudes[1:]) + 1) if len(fft) > 1 else 0
    if not np.any(centered):
        peak = 0
    psd_f, psd = signal.welch(x, fs=rate, nperseg=min(256, len(x)))
    return {"status": "oscillatory" if peak else "no oscillatory signal", "frequency_hz": float(frequencies[peak]), "amplitude": float(amplitudes[peak]), "phase_rad": float(np.angle(fft[peak])) if peak else None, "frequencies_hz": psd_f.tolist(), "psd": psd.tolist()}


def frequency_map(frames):
    if len(frames) < 80:
        return {"status": "Collecting baseline", "samples": len(frames)}
    rate = frames[0].sampling_rate
    if any(f.acoustic_sampling_rate != frames[0].acoustic_sampling_rate or f.sampling_rate != rate or f.source != frames[0].source or f.location_id != frames[0].location_id for f in frames):
        return {"status": "Incompatible acquisition metadata"}
    intervals = np.diff([f.timestamp.timestamp() for f in frames])
    if np.any(np.abs(intervals - 1 / rate) > .1 / rate):
        return {"status": "Irregular acquisition timing; resampling required"}
    values = np.array([[f.values[c] for c in CHANNELS] for f in frames])
    components = {c: spectrum(values[:, i], rate) for i, c in enumerate(CHANNELS[:9])}
    relationships = []
    # Pairwise descriptors use a common spectral bin for phase and coherence.
    for i, j in [(0, 1), (0, 3), (3, 4), (3, 6)]:
        x, y = values[:, i], values[:, j]
        nseg = min(64, len(x) // 2)
        if x.std() > 0 and y.std() > 0:
            frequencies, coherence = signal.coherence(x, y, fs=rate, nperseg=nseg)
        else:
            frequencies = np.fft.rfftfreq(nseg, 1 / rate)
            coherence = np.full(len(frequencies), np.nan)
        target = components[CHANNELS[i]]["frequency_hz"]
        k = int(np.argmin(abs(frequencies - target)))
        _, cross = signal.csd(x, y, fs=rate, nperseg=nseg)
        correlation = signal.correlate(x - x.mean(), y - y.mean(), mode="full")
        lag = int(signal.correlation_lags(len(x), len(y))[int(np.argmax(correlation))])
        denominator = components[CHANNELS[j]]["frequency_hz"]
        ratio = target / denominator if denominator else None
        relationships.append({"pair": [CHANNELS[i], CHANNELS[j]], "harmonic_ratio": ratio, "near_integer_harmonic": bool(ratio and abs(ratio - round(ratio)) < .05), "phase_difference_rad": float(-np.angle(cross[k])) if x.std() > 0 and y.std() > 0 else None, "coherence": float(np.clip(coherence[k], 0, 1)) if np.isfinite(coherence[k]) else None, "coupling": float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else None, "cross_correlation_lag_s": lag / rate if x.std() > 0 and y.std() > 0 else None})
    vector = np.r_[values.mean(axis=0), values.std(axis=0), [components[c]["frequency_hz"] for c in CHANNELS[:9]]]
    audio = np.concatenate([f.acoustic_samples for f in frames])
    acoustic = spectrum(audio, frames[0].acoustic_sampling_rate)
    vector = np.r_[vector, np.sqrt(np.mean(audio ** 2)), acoustic["frequency_hz"]]
    af, times, power = signal.spectrogram(audio, fs=frames[0].acoustic_sampling_rate, nperseg=256, noverlap=128)
    return {"status": "ready", "method": "fm-0.1", "samples": len(frames), "duration_s": len(frames) / rate, "sensor_state": dict(zip(CHANNELS, values.mean(axis=0).tolist())), "components": components, "relationships": relationships, "feature_vector": vector.tolist(), "feature_names": [*[f"mean:{c}" for c in CHANNELS], *[f"std:{c}" for c in CHANNELS], *[f"frequency:{c}" for c in CHANNELS[:9]], "acoustic:rms", "acoustic:frequency"], "acoustic": {**acoustic, "rms": float(np.sqrt(np.mean(audio ** 2))), "unit": "normalized digital amplitude; uncalibrated", "spectrogram": {"frequencies_hz": af.tolist(), "times_s": times[-60:].tolist(), "power": power[:, -60:].tolist()}}}


def compare(a, b):
    if a.get("status") != "ready" or b.get("status") != "ready":
        return {"status": "Insufficient data"}
    delta = (np.array(a["feature_vector"]) - b["feature_vector"]) / FEATURE_SCALES
    distance = float(np.sqrt(np.mean(delta ** 2)))
    rel = [{"pair": x["pair"], "coherence_delta": x["coherence"] - y["coherence"] if x["coherence"] is not None and y["coherence"] is not None else None, "phase_delta_rad": float(np.angle(np.exp(1j * (x["phase_difference_rad"] - y["phase_difference_rad"])))) if x["phase_difference_rad"] is not None and y["phase_difference_rad"] is not None else None} for x, y in zip(a["relationships"], b["relationships"])]
    return {"status": "ready", "similarity": float(np.exp(-distance)), "anomaly_score": distance, "feature_difference": (np.array(a["feature_vector"]) - b["feature_vector"]).tolist(), "normalized_difference": delta.tolist(), "dominant_features": [a["feature_names"][i] for i in np.argsort(abs(delta))[-5:][::-1]], "shared_relationships": [r for r in rel if r["coherence_delta"] is not None and abs(r["coherence_delta"]) < .1 and abs(r["phase_delta_rad"]) < .2], "differential_relationships": [r for r in rel if r["coherence_delta"] is None or abs(r["coherence_delta"]) >= .1 or abs(r["phase_delta_rad"]) >= .2]}


def persistent_invariant(maps):
    qualifying = [m for m in maps if m.get("status") == "ready" and m.get("duration_s", 0) >= 8]
    if len(qualifying) < 3:
        return {"status": "Insufficient runs for PI", "qualifying_runs": len(qualifying)}
    vectors = np.array([m["feature_vector"] for m in qualifying])
    spread = float(np.mean(np.std(vectors / FEATURE_SCALES, axis=0)))
    return {"status": "ready", "method": "median-0.1", "feature_vector": np.median(vectors, axis=0).tolist(), "confidence": float(1 / (1 + spread)), "confidence_definition": "heuristic repeatability score", "qualifying_runs": len(qualifying), "environmental_conditions": [m["sensor_state"] for m in qualifying]}


def state(fm, pi):
    if fm.get("status") != "ready":
        return {"status": "Collecting baseline"}
    base = pi.get("feature_vector")
    dynamic = ((np.array(fm["feature_vector"]) - base) / FEATURE_SCALES).tolist() if base else None
    vector = (np.array(fm["feature_vector"]) / FEATURE_SCALES).tolist()
    payload = {"method": "pa-0.1", "pi": base, "dynamic": dynamic, "relationships": fm["relationships"], "normalized_feature_vector": vector}
    identifier = hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()[:24]
    return {**payload, "status": "ready" if base else "PA preliminary", "identifier": identifier}
