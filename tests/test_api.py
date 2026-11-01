import time
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import pyarrow.parquet as pq
from lab.app import create_app
from lab.engine import frequency_map
from lab.simulator import Simulator


def test_live_lifecycle_events_restart_and_archive(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        assert client.post('/api/events', json={"kind": "Door opened"}).status_code == 409
        run = client.post('/api/runs', json={"room": "Room A"}).json()
        assert client.post('/api/runs', json={}).status_code == 409
        with client.websocket_connect('/ws') as ws:
            data = ws.receive_json()
            assert data["run"]["id"] == run["id"]
        time.sleep(.2)
        event = client.post('/api/events', json={"kind": "Door opened", "note": "test"}).json()
        assert datetime.fromisoformat(event["timestamp"]).tzinfo
        assert client.post('/api/perturbations', json={}).status_code == 409
        saved = client.post('/api/stop', json={}).json()
        assert saved["status"] == "complete"
        archive = client.get('/api/runs/'+run["id"]).json()
        assert len(archive["frames"]) >= 2
        assert archive["events"][0] == event
        assert client.get('/').status_code == 200
    with TestClient(create_app(tmp_path)) as client:
        assert len(client.get('/api/runs').json()) == 1
        assert client.get('/api/runs/'+run["id"]).json()["events"][0] == event
    files = list(tmp_path.glob('raw/**/*.parquet'))
    assert len(files) == 1
    assert pq.read_table(files[0]).num_rows >= 2
    assert list(tmp_path.glob('raw/**/*.wav'))
    assert list(tmp_path.glob('derived/*.json'))


def test_completed_room_comparison_and_response_windows(tmp_path):
    app = create_app(tmp_path)
    # Seed the same canonical frames used by acquisition to avoid 30s wall-clock tests.
    with TestClient(app) as client:
        lab = app.state.lab
        start = datetime.now(timezone.utc) - timedelta(seconds=16)
        for room in ('Room A', 'Room B'):
            run = client.post('/api/runs', json={"room": room}).json()
            sim = Simulator(room, run['id'], start=start)
            data = [sim.frame(tone=(440, .1) if 5 <= i/20 < 10 else None) for i in range(320)]
            # Route mutations onto the application's event loop.
            async def seed():
                lab.store.db.execute("DELETE FROM frames WHERE run_id=?", [run["id"]])
                lab.frames = data
                lab.fm = frequency_map(data)
                for frame in data: lab.store.append(frame)
                lab.pending = {"start_epoch": start.timestamp()+5, "stop_epoch": start.timestamp()+10, "pre_s": 4, "post_s": 4, "kind": "single", "frequency_hz": 440, "amplitude": .1}
                lab.finish_response()
                return lab.stop()
            assert client.portal.call(seed)["status"] == "complete"
            archive = client.get('/api/runs/'+run['id']).json()
            assert archive['responses'][0]['status'] == 'ready'
            assert archive['responses'][0]['during_state']['acoustic']['rms'] > .05
        comparison = client.get('/api/compare').json()
        assert comparison['status'] == 'ready'
        assert comparison['similarity'] < .8
        assert comparison['responses']['Room A']


def test_hardware_mode_no_fallback_and_local_origin(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.post('/api/runs', json={"source": "serial"}).status_code == 422
        assert client.post('/api/runs', json={"source": "serial", "port": "/not/a/device"}).status_code == 400
        assert client.get('/api/status').json()['latest'] is None
        assert client.post('/api/runs', json={}, headers={"Origin": "https://other.example"}).status_code == 403


def test_summarized_storage_and_selected_raw_interval(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        run = client.post('/api/runs', json={"retention": "summarized"}).json()
        time.sleep(5.2)
        async def counts():
            lab = client.app.state.lab
            return len(lab.store.frames(run['id'])), len(lab.store.records('summaries', run['id']))
        raw, summary = client.portal.call(counts)
        assert raw == 0
        assert summary >= 1
        assert client.post('/api/raw/true', json={}).json()['manual_raw']
        time.sleep(.2)
        assert client.post('/api/stop', json={}).status_code == 200
        archived = client.get('/api/runs/'+run['id']).json()
        assert len(archived['frames']) >= 80
        assert archived['summaries'][0]['fm']['status'] == 'ready'
        assert archived['fm']['status'] == 'ready'
        assert list(tmp_path.glob('derived/*.parquet'))
