import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
import json
from pathlib import Path
import time
import uuid
import numpy as np

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal

from .engine import compare, frequency_map, persistent_invariant, state
from .schema import UNITS
from .serial_gateway import SerialGateway, ports
from .simulator import Simulator
from .storage import Storage


def now():
    return datetime.now(timezone.utc).isoformat()


class Start(BaseModel):
    room: Literal["Room A", "Room B"] = "Room A"
    source: Literal["simulation", "serial"] = "simulation"
    baseline: bool = True
    seed: int = 1
    port: str | None = None
    disturbance: float = Field(default=0, ge=0, le=20)
    retention: Literal["full", "summarized"] = "full"


class Event(BaseModel):
    kind: str = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=2000)


class Perturbation(BaseModel):
    kind: Literal["single", "stepped", "linear", "logarithmic"] = "single"
    frequency_hz: float = Field(default=440, ge=20, le=3000)
    end_frequency_hz: float = Field(default=880, ge=20, le=3000)
    amplitude: float = Field(default=.05, gt=0, le=.25)
    duration_s: float = Field(default=4, ge=4, le=120)
    pre_s: float = Field(default=4, ge=4, le=30)
    post_s: float = Field(default=4, ge=4, le=30)


class Lab:
    def __init__(self, root):
        self.store = Storage(root)
        self.active = None
        self.frames = []
        self.gateway = None
        self.error = None
        self.perturbation = None
        self.pending = None
        self.fm = {"status": "Collecting baseline"}
        self.next_sample = time.monotonic()
        self.last_received = None
        self.manual_raw = False
        self.sample_count = 0
        self.anomaly_until = 0
        for run in self.store.runs():
            if run["status"] == "recording":
                run["status"] = "interrupted"
                run["stopped_at"] = now()
                self.store.save_run(run)

    def pi(self, room, source):
        runs = [r for r in self.store.runs() if r["room"] == room and r["source"] == source and r["baseline"] and r["status"] == "complete" and not r.get("has_perturbation")]
        return persistent_invariant([r.get("fm", {}) for r in runs])

    def snapshot(self):
        room = self.active["room"] if self.active else (self.frames[-1].location_id if self.frames else "Room A")
        source = self.active["source"] if self.active else (self.frames[-1].source if self.frames else "simulation")
        pi = self.pi(room, source)
        baselines = [r for r in self.store.runs() if r["room"] == room and r["source"] == source and r["baseline"] and r["status"] == "complete" and not r.get("has_perturbation") and r.get("fm", {}).get("status") == "ready"]
        responses = self.store.records("responses", self.active["id"]) if self.active else []
        traces = [{"timestamp": f.timestamp.isoformat(), "values": f.values, "acoustic_rms": float(np.sqrt(np.mean(np.square(f.acoustic_samples))))} for f in self.frames[-200:]]
        return {"run": self.active, "connected": bool(self.active and self.last_received and time.monotonic() - self.last_received < 2 and self.error is None), "error": self.error, "latest": self.frames[-1].model_dump(mode="json") if self.frames else None, "trace_window": traces, "fm": self.fm, "pi": pi, "pa": state(self.fm, pi), "baseline": compare(self.fm, baselines[0]["fm"]) if baselines else {"status": "Collecting baseline"}, "comparison_target": baselines[0]["id"] if baselines else None, "response": responses[-1] if responses else None, "perturbation": self.perturbation, "post_window_pending": self.pending is not None, "manual_raw": self.manual_raw, "units": UNITS}

    def finish_response(self):
        p = self.pending
        if not p:
            return
        start, stop = p["start_epoch"], p["stop_epoch"]
        before = [f for f in self.frames if start - p["pre_s"] <= f.timestamp.timestamp() < start]
        during = [f for f in self.frames if start <= f.timestamp.timestamp() < stop]
        after = [f for f in self.frames if stop <= f.timestamp.timestamp() <= stop + p["post_s"]]
        pre, mid, post = map(frequency_map, [before, during, after])
        payload = {**p, "pre_state": pre, "during_state": mid, "post_state": post, "response": compare(post, pre), "during_response": compare(mid, pre), "recovery": {"residual_vs_pre": compare(post, pre), "change_since_during": compare(post, mid)}, "status": "ready" if all(m.get("status") == "ready" for m in [pre, mid, post]) else "Insufficient recorded windows"}
        self.store.add("responses", self.active["id"], payload)
        self.pending = None

    async def loop(self):
        while True:
            if not self.active:
                await asyncio.sleep(.05)
                continue
            try:
                tone = None
                if self.perturbation:
                    p = self.perturbation
                    elapsed = time.time() - p["start_epoch"]
                    progress = min(1, elapsed / p["duration_s"])
                    if elapsed >= p["duration_s"]:
                        self.stop_tone()
                    else:
                        a, b = p["frequency_hz"], p["end_frequency_hz"]
                        f = a
                        if p["kind"] == "linear": f = a + (b-a) * progress
                        if p["kind"] == "logarithmic": f = a * (b/a) ** progress
                        if p["kind"] == "stepped": f = a + (b-a) * min(3, int(progress*4)) / 3
                        tone = (f, p["amplitude"])
                if self.active["source"] == "simulation":
                    frame = self.sim.frame(self.active["disturbance"], tone)
                else:
                    current_run = self.active
                    frame = await asyncio.to_thread(self.gateway.read, current_run["id"], current_run["room"])
                    if self.active is not current_run:
                        continue
                if frame:
                    if self.frames and frame.timestamp <= self.frames[-1].timestamp:
                        raise ValueError("Device timestamps must increase monotonically")
                    self.last_received = time.monotonic()
                    self.frames.append(frame)
                    self.frames = self.frames[-4000:]
                    self.sample_count += 1
                    self.error = None
                    if self.sample_count % 20 == 0:
                        self.fm = frequency_map(self.frames[-400:])
                        score = self.snapshot()["baseline"].get("anomaly_score", 0)
                        if score > 2:
                            self.anomaly_until = time.time() + 4
                            for prior in self.frames[-80:]: self.store.append(prior)
                    if self.active["retention"] == "full" or self.manual_raw or self.perturbation or self.pending or time.time() < self.anomaly_until:
                        self.store.append(frame)
                    if self.sample_count % 100 == 0:
                        self.store.add("summaries", self.active["id"], {"timestamp": frame.timestamp.isoformat(), "fm": frequency_map(self.frames[-100:])})
                if self.pending and time.time() >= self.pending["stop_epoch"] + self.pending["post_s"]:
                    self.finish_response()
            except Exception as e:
                self.error = str(e)
            if self.active and self.active["source"] == "simulation":
                self.next_sample += .05
                await asyncio.sleep(max(0, self.next_sample - time.monotonic()))
            else:
                await asyncio.sleep(.005)

    def stop_tone(self):
        if self.perturbation:
            self.pending = {**self.perturbation, "stopped_at": now(), "stop_epoch": time.time()}
            self.store.add("events", self.active["id"], {"timestamp": now(), "kind": "Tone stopped"})
            self.perturbation = None

    def stop(self):
        self.stop_tone()
        self.finish_response()
        if self.gateway:
            self.gateway.close()
            self.gateway = None
        self.fm = frequency_map(self.frames[-400:])
        self.active.update(status="complete" if not self.error else "acquisition_error", stopped_at=now(), fm=self.fm)
        self.store.export(self.active["id"], self.store.frames(self.active["id"]), {"fm": self.active["fm"], "pi": self.pi(self.active["room"], self.active["source"]), "responses": self.store.records("responses", self.active["id"])})
        self.store.save_run(self.active)
        self.active["pi"] = self.pi(self.active["room"], self.active["source"])
        self.active["pa"] = state(self.fm, self.active["pi"])
        self.store.save_run(self.active)
        (self.store.root / "derived" / f"{self.active['id']}-state.json").write_text(json.dumps({"pi": self.active["pi"], "pa": self.active["pa"]}, allow_nan=False))
        run = self.active
        self.active = None
        return run


def create_app(root=None):
    @asynccontextmanager
    async def lifespan(app):
        lab = Lab(root or os.environ.get("LAB_DATA_DIR", "data"))
        app.state.lab = lab
        task = asyncio.create_task(lab.loop())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        if lab.active:
            lab.stop()
        lab.store.db.close()

    app = FastAPI(title="Elyrion Frequency Lab", lifespan=lifespan)

    def lab(): return app.state.lab

    @app.middleware("http")
    async def local_origin(request, call_next):
        origin = request.headers.get("origin")
        if origin and origin not in ("http://127.0.0.1:8765", "http://localhost:8765"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Local origin required"}, status_code=403)
        return await call_next(request)

    @app.get("/api/status")
    async def status(): return lab().snapshot()

    @app.get("/api/ports")
    async def serial_ports(): return ports()

    @app.post("/api/runs")
    async def start(body: Start):
        l = lab()
        if l.active: raise HTTPException(409, "Stop the current run first")
        if body.source == "serial":
            if not body.port: raise HTTPException(422, "Select a serial port")
            try: l.gateway = SerialGateway(body.port)
            except Exception as e: raise HTTPException(400, str(e)) from e
        run = {"id": str(uuid.uuid4()), **body.model_dump(), "started_at": now(), "status": "recording"}
        l.frames, l.fm, l.error = [], {"status": "Collecting baseline"}, None
        l.perturbation = l.pending = None
        l.sim = Simulator(body.room, run["id"], body.seed)
        l.next_sample = time.monotonic()
        l.last_received = None
        l.sample_count = 0
        l.manual_raw = False
        l.anomaly_until = 0
        l.store.save_run(run)
        l.active = run
        return run

    @app.post("/api/stop")
    async def stop():
        if not lab().active: raise HTTPException(409, "No active run")
        return lab().stop()

    @app.post("/api/events")
    async def event(body: Event):
        if not lab().active: raise HTTPException(409, "No active run")
        event = {"timestamp": now(), **body.model_dump()}
        lab().store.add("events", lab().active["id"], event)
        return event

    @app.post("/api/perturbations")
    async def perturb(body: Perturbation):
        l = lab()
        if not l.active: raise HTTPException(409, "No active run")
        if l.perturbation or l.pending: raise HTTPException(409, "Wait for the current perturbation post-window")
        if not l.frames or (l.frames[-1].timestamp - l.frames[0].timestamp).total_seconds() < body.pre_s:
            raise HTTPException(409, "Collect the configured pre-window first")
        l.active["has_perturbation"] = True
        for frame in l.frames:
            if frame.timestamp.timestamp() >= time.time() - body.pre_s:
                l.store.append(frame)
        l.perturbation = {"id": str(uuid.uuid4()), **body.model_dump(), "started_at": now(), "start_epoch": time.time(), "actuation": "synthetic injection" if l.active["source"] == "simulation" else "browser audio requested; physical playback unverified"}
        l.store.save_run(l.active)
        l.store.add("events", l.active["id"], {"timestamp": now(), "kind": "Tone started", "perturbation": l.perturbation})
        return l.perturbation

    @app.post("/api/perturbations/stop")
    async def stop_perturbation():
        lab().stop_tone()
        return {"status": "stopped; collecting post-window"}

    @app.post("/api/raw/{enabled}")
    async def retain_raw(enabled: bool):
        if not lab().active: raise HTTPException(409, "No active run")
        lab().manual_raw = enabled
        if enabled:
            for frame in lab().frames[-80:]: lab().store.append(frame)
        lab().store.add("events", lab().active["id"], {"timestamp": now(), "kind": "Raw retention started" if enabled else "Raw retention stopped"})
        return {"manual_raw": enabled}

    @app.get("/api/runs")
    async def runs(): return lab().store.runs()

    @app.get("/api/runs/{run_id}")
    async def archive(run_id: str):
        run = next((r for r in lab().store.runs() if r["id"] == run_id), None)
        if not run: raise HTTPException(404, "Run not found")
        frames = lab().store.frames(run_id)
        fm = run.get("fm", frequency_map(frames))
        pi = run.get("pi", lab().pi(run["room"], run["source"]))
        return {"run": run, "frames": [f.model_dump(mode="json") for f in frames], "fm": fm, "pi": pi, "pa": state(fm, pi), "summaries": lab().store.records("summaries", run_id), "events": lab().store.records("events", run_id), "responses": lab().store.records("responses", run_id)}

    @app.get("/api/compare")
    async def rooms(source: Literal["simulation", "serial"] = "simulation"):
        selected = {}
        for room in ("Room A", "Room B"):
            selected[room] = next((r for r in lab().store.runs() if r["room"] == room and r["source"] == source and r["status"] == "complete" and r.get("fm", {}).get("status") == "ready"), None)
        if not all(selected.values()): return {"status": "Record and stop a qualifying run in each room"}
        a, b = selected.values()
        pa, pb = lab().pi("Room A", source), lab().pi("Room B", source)
        return {**compare(a["fm"], b["fm"]), "runs": {r: v["id"] for r, v in selected.items()}, "fm": {r: v["fm"] for r, v in selected.items()}, "pi": {"Room A": pa, "Room B": pb}, "pa": {"Room A": state(a["fm"], pa), "Room B": state(b["fm"], pb)}, "responses": {"Room A": lab().store.records("responses", a["id"]), "Room B": lab().store.records("responses", b["id"])}}

    @app.websocket("/ws")
    async def live(ws: WebSocket):
        if ws.headers.get("origin") not in (None, "http://127.0.0.1:8765", "http://localhost:8765"):
            await ws.close(code=1008)
            return
        await ws.accept()
        try:
            while True:
                await ws.send_json(lab().snapshot())
                await asyncio.sleep(.5)
        except WebSocketDisconnect:
            pass

    dist = Path(__file__).resolve().parent.parent / "ui/dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
        @app.get("/")
        async def index(): return FileResponse(dist / "index.html")
    return app


app = create_app()
