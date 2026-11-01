"""Newline-delimited canonical JSON; no synthetic fallback in hardware mode."""
import serial
import json
import time
from serial.tools import list_ports
from .schema import Frame


def ports():
    return [{"port": p.device, "description": p.description} for p in list_ports.comports()]


class SerialGateway:
    def __init__(self, port):
        self.connection = serial.Serial(port, 115200, timeout=.1)
        self.connection.reset_input_buffer()
        self.connection.write((json.dumps({"command": "start", "epoch_ms": int(time.time() * 1000)}) + "\n").encode())

    def read(self, run_id, location):
        line = self.connection.readline(131073)
        if not line:
            return None
        if len(line) > 131072 or not line.endswith(b"\n"):
            raise ValueError("incomplete or oversized serial frame")
        frame = Frame.model_validate_json(line)
        if frame.source != "serial":
            raise ValueError("hardware must identify source=serial")
        return frame.model_copy(update={"run_id": run_id, "location_id": location})

    def close(self):
        self.connection.close()
