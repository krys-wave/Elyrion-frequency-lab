import json
from lab.serial_gateway import SerialGateway
from lab.simulator import Simulator


def test_serial_frame_uses_same_canonical_schema(monkeypatch):
    frame = Simulator().frame().model_dump(mode="json")
    frame['source'] = 'serial'
    class Connection:
        def reset_input_buffer(self): pass
        def readline(self, size): return (json.dumps(frame)+'\n').encode()
        def write(self, data): return len(data)
        def close(self): pass
    monkeypatch.setattr('lab.serial_gateway.serial.Serial', lambda *a, **kw: Connection())
    gateway = SerialGateway('mock')
    received = gateway.read('new-run', 'Room B')
    assert received.run_id == 'new-run'
    assert received.location_id == 'Room B'
    assert received.source == 'serial'
    assert received.values == frame['values']
