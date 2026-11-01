from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
import numpy as np

CHANNELS = ["M_X", "M_Y", "M_Z", "A_X", "A_Y", "A_Z", "G_X", "G_Y", "G_Z", "Temp", "H", "Pressure"]
UNITS = dict(zip(CHANNELS, ["T"] * 3 + ["m/s²"] * 3 + ["rad/s"] * 3 + ["K", "fraction", "Pa"]))


class Frame(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    timestamp: datetime
    device_id: str = Field(min_length=1)
    firmware_version: str = Field(min_length=1)
    sampling_rate: float = Field(gt=0, le=20000)
    acoustic_sampling_rate: int = Field(gt=0, le=192000)
    calibration: dict = Field(default_factory=dict)
    run_id: str
    location_id: Literal["Room A", "Room B"]
    source: Literal["simulation", "serial"]
    values: dict[str, float]
    acoustic_samples: list[float] = Field(min_length=1, max_length=8192)

    @field_validator("timestamp")
    @classmethod
    def aware_timestamp(cls, value):
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value

    @field_validator("values")
    @classmethod
    def valid_channels(cls, value):
        if set(value) != set(CHANNELS) or not np.isfinite(list(value.values())).all():
            raise ValueError("all canonical channels must be finite")
        return value

    @field_validator("acoustic_samples")
    @classmethod
    def finite_audio(cls, value):
        if not np.isfinite(value).all():
            raise ValueError("audio must be finite")
        return value
