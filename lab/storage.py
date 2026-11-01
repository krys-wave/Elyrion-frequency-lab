import json
from pathlib import Path
import wave
import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from .schema import Frame


class Storage:
    def __init__(self, root):
        self.root = Path(root)
        for folder in ["database", "raw", "derived", "exports"]:
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        self.db = duckdb.connect(str(self.root / "database/lab.duckdb"))
        self.db.execute("CREATE TABLE IF NOT EXISTS runs (id VARCHAR PRIMARY KEY, payload JSON)")
        self.db.execute("CREATE TABLE IF NOT EXISTS frames (run_id VARCHAR, timestamp VARCHAR, payload JSON, PRIMARY KEY(run_id, timestamp))")
        self.db.execute("CREATE TABLE IF NOT EXISTS events (run_id VARCHAR, payload JSON)")
        self.db.execute("CREATE TABLE IF NOT EXISTS responses (run_id VARCHAR, payload JSON)")
        self.db.execute("CREATE TABLE IF NOT EXISTS summaries (run_id VARCHAR, payload JSON)")

    def save_run(self, run):
        self.db.execute("INSERT OR REPLACE INTO runs VALUES (?, ?)", [run["id"], json.dumps(run)])

    def runs(self):
        return [json.loads(r[0]) for r in self.db.execute("SELECT payload FROM runs ORDER BY json_extract_string(payload, '$.started_at') DESC").fetchall()]

    def frames(self, run_id):
        return [Frame.model_validate_json(r[0]) for r in self.db.execute("SELECT payload FROM frames WHERE run_id=? ORDER BY json_extract_string(payload, '$.timestamp')", [run_id]).fetchall()]

    def append(self, frame):
        self.db.execute("INSERT OR IGNORE INTO frames VALUES (?, ?, ?)", [frame.run_id, frame.timestamp.isoformat(), frame.model_dump_json()])

    def add(self, table, run_id, payload):
        assert table in ("events", "responses", "summaries")
        self.db.execute(f"INSERT INTO {table} VALUES (?, ?)", [run_id, json.dumps(payload)])

    def records(self, table, run_id):
        assert table in ("events", "responses", "summaries")
        return [json.loads(r[0]) for r in self.db.execute(f"SELECT payload FROM {table} WHERE run_id=?", [run_id]).fetchall()]

    def export(self, run_id, frames, derived):
        if frames:
            directory = self.root / "raw" / frames[0].location_id.replace(" ", "_") / run_id
            directory.mkdir(parents=True, exist_ok=True)
            rows = [{**f.model_dump(mode="json", exclude={"values", "calibration"}), **f.values, "calibration_json": json.dumps(f.calibration)} for f in frames]
            pq.write_table(pa.Table.from_pylist(rows), directory / "measurements.parquet")
            audio = np.concatenate([f.acoustic_samples for f in frames])
            with wave.open(str(directory / "audio.wav"), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(frames[0].acoustic_sampling_rate)
                wav.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
        (self.root / "derived" / f"{run_id}.json").write_text(json.dumps(derived, indent=2, allow_nan=False))
        summaries = self.records("summaries", run_id)
        if summaries:
            pq.write_table(pa.Table.from_pylist([{"timestamp": s["timestamp"], "map_json": json.dumps(s["fm"])} for s in summaries]), self.root / "derived" / f"{run_id}.parquet")
