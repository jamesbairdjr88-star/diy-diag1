"""Intake data model."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class Vehicle:
    vin: str = ""
    year: Optional[int] = None
    make: str = ""
    model: str = ""
    engine: str = ""
    transmission: str = ""
    mileage: Optional[int] = None


@dataclass
class Intake:
    vehicle: Vehicle
    concern: str                      # owner's own words
    onset: str = ""                   # e.g. "2 weeks ago, gradual"
    frequency: str = ""               # always / sometimes / once
    engine_temp: str = ""             # cold / warm / both
    speed_range: str = ""             # e.g. "40-50 mph"
    driving_condition: List[str] = field(default_factory=list)  # idle, accelerating, braking, turning, cruising, highway
    weather: str = ""
    warning_lights: List[str] = field(default_factory=list)     # check engine, flashing check engine, abs, airbag, battery, oil, temp
    codes: List[str] = field(default_factory=list)              # e.g. P0300
    recent_work: str = ""
    modifications: str = ""
    tools_available: List[str] = field(default_factory=list)    # obd2 scanner, multimeter, jack stands, torque wrench

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Intake":
        d = dict(d)
        v = Vehicle(**d.pop("vehicle", {}))
        return cls(vehicle=v, **d)

    def text_blob(self) -> str:
        parts = [self.concern, self.onset, self.frequency, self.engine_temp, self.speed_range,
                 " ".join(self.driving_condition), self.weather, " ".join(self.warning_lights),
                 self.recent_work]
        return " ".join(p for p in parts if p).lower()
