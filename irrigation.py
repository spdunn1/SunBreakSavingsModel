# load_synth/irrigation.py
"""
Irrigation system models: efficiency, run patterns, and scheduling flexibility.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class IrrigationSystem:
    name: str
    display_name: str
    efficiency: float
    pump_loading_factor: float
    min_run_block_hr: float
    max_run_block_hr: float
    scheduling_flexibility: float
    labor_hours: List[int] = field(default_factory=list)
    baseline_hourly_weights: List[float] = field(default_factory=list)
    soil_buffer_fraction: float = 0.15
    description: str = ""


CENTER_PIVOT = IrrigationSystem(
    name="center_pivot",
    display_name="Center Pivot",
    efficiency=0.85,
    pump_loading_factor=0.88,
    min_run_block_hr=8.0,
    max_run_block_hr=48.0,
    scheduling_flexibility=0.90,
    labor_hours=[],
    soil_buffer_fraction=0.20,
    baseline_hourly_weights=[
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        0.07, 0.08, 0.08, 0.08, 0.07, 0.07,
        0.07, 0.07, 0.07, 0.07, 0.06, 0.05,
        0.04, 0.04, 0.03, 0.02, 0.02, 0.01,
    ],
    description="Large central motor drives revolving lateral arm. Fully automated, excellent TOU shifting candidate."
)

DRIP = IrrigationSystem(
    name="drip",
    display_name="Drip / Micro-Irrigation",
    efficiency=0.92,
    pump_loading_factor=0.85,
    min_run_block_hr=0.5,
    max_run_block_hr=8.0,
    scheduling_flexibility=0.75,
    labor_hours=[],
    soil_buffer_fraction=0.10,
    baseline_hourly_weights=[
        0.0, 0.0, 0.0, 0.0, 0.0, 0.01,
        0.06, 0.08, 0.09, 0.09, 0.09, 0.09,
        0.09, 0.09, 0.08, 0.07, 0.06, 0.04,
        0.03, 0.03, 0.02, 0.01, 0.01, 0.01,
    ],
    description="Low-volume emitters at root zone. Highest efficiency. Most common for tree crops."
)

FLOOD = IrrigationSystem(
    name="flood",
    display_name="Flood / Furrow",
    efficiency=0.62,
    pump_loading_factor=0.82,
    min_run_block_hr=6.0,
    max_run_block_hr=24.0,
    scheduling_flexibility=0.30,
    labor_hours=[6, 7, 8, 9, 16, 17, 18],
    soil_buffer_fraction=0.30,
    baseline_hourly_weights=[
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        0.05, 0.10, 0.10, 0.09, 0.09, 0.08,
        0.07, 0.07, 0.06, 0.06, 0.06, 0.06,
        0.05, 0.04, 0.02, 0.01, 0.0, 0.0,
    ],
    description="Gravity or low-head pump floods field rows. Highest labor, lowest efficiency. Limited TOU optimization."
)

SPRINKLER = IrrigationSystem(
    name="sprinkler",
    display_name="Wheel Line / Set-Move Sprinkler",
    efficiency=0.78,
    pump_loading_factor=0.87,
    min_run_block_hr=4.0,
    max_run_block_hr=12.0,
    scheduling_flexibility=0.50,
    labor_hours=[6, 7, 8, 17, 18, 19],
    soil_buffer_fraction=0.15,
    baseline_hourly_weights=[
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        0.04, 0.09, 0.10, 0.10, 0.09, 0.08,
        0.07, 0.07, 0.06, 0.06, 0.07, 0.07,
        0.05, 0.04, 0.04, 0.02, 0.01, 0.01,
    ],
    description="Portable aluminum pipe laterals. Medium TOU optimization potential for start-time shifts."
)

IRRIGATION_SYSTEMS = {
    "center_pivot": CENTER_PIVOT,
    "drip": DRIP,
    "flood": FLOOD,
    "sprinkler": SPRINKLER,
}
