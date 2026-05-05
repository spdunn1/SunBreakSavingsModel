# load_synth/engine.py
"""
Load synthesis engine.

Converts farm physical parameters → 8760-hour pump load profile (kW).

Pipeline:
  1. Compute daily ETc from ETo × Kc for each day of year
  2. Convert ETc to gross water volume (acre-inches) accounting for irrigation efficiency
  3. Convert water volume to pump runtime hours using pump power and wire-to-water efficiency
  4. Distribute runtime across hours using system archetype weights (baseline)
     OR optimized TOU-aware schedule (via scheduler module)

ETo source: synthetic TMY shape calibrated to California climate regions,
or actual CIMIS data when available.
"""

import datetime
import math
from typing import List, Optional, Tuple

from .crops import CropProfile, CROPS
from .irrigation import IrrigationSystem, IRRIGATION_SYSTEMS


# ─────────────────────────────────────────────────────────────────────────────
# California climate region ETo shapes (monthly average, inches/day)
# Source: CIMIS historical averages by region
# Used as TMY stand-in when CIMIS API is not called
# ─────────────────────────────────────────────────────────────────────────────
CLIMATE_REGIONS = {
    "central_valley": {
        "name": "Central Valley (Fresno/Bakersfield)",
        "eto_monthly": [0.06, 0.10, 0.17, 0.22, 0.27, 0.32, 0.35, 0.31, 0.24, 0.16, 0.09, 0.05],
    },
    "sacramento_valley": {
        "name": "Sacramento Valley (Sacramento/Chico)",
        "eto_monthly": [0.05, 0.09, 0.15, 0.20, 0.25, 0.30, 0.33, 0.30, 0.22, 0.14, 0.07, 0.04],
    },
    "coastal_central": {
        "name": "Central Coast (Salinas/Santa Maria)",
        "eto_monthly": [0.07, 0.09, 0.12, 0.15, 0.17, 0.18, 0.19, 0.18, 0.16, 0.13, 0.09, 0.07],
    },
    "southern_california": {
        "name": "Southern CA (San Diego/Ventura)",
        "eto_monthly": [0.08, 0.10, 0.14, 0.17, 0.20, 0.22, 0.24, 0.23, 0.20, 0.15, 0.10, 0.08],
    },
    "coachella_imperial": {
        "name": "Coachella/Imperial Valley (Desert)",
        "eto_monthly": [0.10, 0.15, 0.22, 0.28, 0.35, 0.40, 0.43, 0.40, 0.33, 0.24, 0.14, 0.10],
    },
}


def _days_in_month(month: int, year: int = 2024) -> int:
    if month == 12:
        return 31
    return (datetime.date(year, month + 1, 1) - datetime.date(year, month, 1)).days


def compute_daily_etc(
    crop: CropProfile,
    climate_region: str,
    year: int = 2024,
) -> List[Tuple[datetime.date, float]]:
    """
    Compute daily ETc (inches/day) for a full year.

    Returns list of (date, etc_in_day) for all 365/366 days.
    ETc = ETo × Kc, interpolated to daily resolution from monthly averages.
    """
    region = CLIMATE_REGIONS[climate_region]
    eto_monthly = region["eto_monthly"]

    daily_etc = []
    for month in range(1, 13):
        n_days = _days_in_month(month, year)
        eto_day = eto_monthly[month - 1]  # inches/day for this month
        kc = crop.kc_at_month(month)
        etc_day = eto_day * kc

        for day in range(1, n_days + 1):
            date = datetime.date(year, month, day)
            daily_etc.append((date, etc_day))

    return daily_etc


def compute_pump_runtime_hours(
    etc_in_day: float,
    area_acres: float,
    system: IrrigationSystem,
    pump_kw: float,
    total_dynamic_head_ft: float,
    pump_efficiency: float = 0.68,
    motor_efficiency: float = 0.92,
) -> float:
    """
    Convert ETc (inches/day) for a field area into pump runtime hours.

    Hydraulic flow-rate method (physically correct):
      GPM = pump_kW_actual × pump_eff × motor_eff × 3960 / (TDH × 0.746)
      volume_gal = gross_ETc_in × area_acres × 27154 gal/acre-inch
      runtime_hr = volume_gal / GPM / 60

    Note: runtime is TDH-independent at a given pump kW (higher TDH means
    less flow AND more energy per gallon — they cancel out in the runtime calc).
    TDH only affects energy consumption, not runtime for a sized pump.

    Args:
        etc_in_day: Crop ET inches/day
        area_acres: Irrigated area
        system: IrrigationSystem archetype (provides efficiency and loading factor)
        pump_kw: Pump nameplate power (kW)
        total_dynamic_head_ft: TDH (used only for GPM calculation)
        pump_efficiency: Pump hydraulic efficiency (default 0.68)
        motor_efficiency: Motor efficiency (default 0.92)

    Returns:
        Pump runtime hours for that day (0.0 if ETc is 0)
    """
    if etc_in_day <= 0 or pump_kw <= 0:
        return 0.0

    actual_kw = pump_kw * system.pump_loading_factor

    # Flow rate from pump curve (GPM)
    gpm = (actual_kw * pump_efficiency * motor_efficiency * 3960) / (
        total_dynamic_head_ft * 0.746
    )
    if gpm <= 0:
        return 0.0

    # Gross water requirement
    gross_etc = etc_in_day / system.efficiency
    volume_gal = gross_etc * area_acres * 27154  # 27154 gal per acre-inch

    # Runtime in hours
    runtime_hr = (volume_gal / gpm) / 60.0
    return runtime_hr


def build_baseline_load_profile(
    crop_name: str,
    irrigation_type: str,
    climate_region: str,
    area_acres: float,
    pump_kw: float,
    total_dynamic_head_ft: Optional[float] = None,
    pump_efficiency: float = 0.68,
    motor_efficiency: float = 0.92,
    year: int = 2024,
) -> List[float]:
    """
    Build the baseline 8760-hour load profile (kW) representing current
    farmer behavior without SunBreak optimization.

    Uses the BaselineScheduler which distributes runtime across hours using
    system archetype weights. Pump runs at rated kW for fractional hours
    (i.e., partial hours are modeled as partial-on at full rated power,
    which is equivalent to the pump running for that fraction of the hour).
    """
    from scheduler.optimizer import BaselineScheduler

    crop = CROPS[crop_name]
    system = IRRIGATION_SYSTEMS[irrigation_type]

    if total_dynamic_head_ft is None:
        total_dynamic_head_ft = crop.typical_tdh_ft

    daily_etc = compute_daily_etc(crop, climate_region, year)
    scheduler = BaselineScheduler()

    hourly_load = []
    for day_offset, (date, etc_day) in enumerate(daily_etc):
        if day_offset >= 365:
            break

        runtime_hr = compute_pump_runtime_hours(
            etc_day, area_acres, system, pump_kw,
            total_dynamic_head_ft, pump_efficiency, motor_efficiency
        )
        runtime_hr = min(runtime_hr, 23.0)

        # No-op days (crop dormant, no irrigation needed)
        if runtime_hr <= 0:
            hourly_load.extend([0.0] * 24)
            continue

        # Use actual dummy rates — baseline doesn't optimize so rates don't matter
        dummy_rates = [0.15] * 24
        day_load = scheduler.schedule_day(runtime_hr, system, dummy_rates, [0.0]*24, pump_kw)
        hourly_load.extend(day_load)

    while len(hourly_load) < 8760:
        hourly_load.append(0.0)

    return hourly_load[:8760]


def build_load_profile_summary(hourly_load: List[float]) -> dict:
    """Compute summary statistics for a load profile."""
    non_zero = [v for v in hourly_load if v > 0]
    total_kwh = sum(hourly_load)
    peak_kw = max(hourly_load) if hourly_load else 0

    # Monthly energy
    monthly_kwh = {}
    start = datetime.date(2024, 1, 1)
    for h, kw in enumerate(hourly_load):
        date = start + datetime.timedelta(hours=h)
        month = date.month
        monthly_kwh[month] = monthly_kwh.get(month, 0) + kw

    return {
        "total_kwh": round(total_kwh, 1),
        "peak_kw": round(peak_kw, 2),
        "avg_kw_operating": round(sum(non_zero) / len(non_zero), 2) if non_zero else 0,
        "operating_hours": len(non_zero),
        "monthly_kwh": {k: round(v, 1) for k, v in sorted(monthly_kwh.items())},
    }
