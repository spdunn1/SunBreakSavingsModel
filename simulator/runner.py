# simulator/runner.py
"""
High-level simulation runner.

run_simulation() is the main entry point — takes a FarmConfig and
returns a SavingsReport with the full baseline vs optimized comparison.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from typing import Optional, List

from tariffs import REGISTRY
from tariffs.models import NEM_PROGRAM, build_nem2_export_schedule, build_nbt_export_schedule
from load_synth.engine import build_baseline_load_profile
from solar.profiles import PVSystem, generate_solar_profile
from scheduler.optimizer import build_optimized_load_profile
from simulator.core import simulate, SavingsReport


@dataclass
class FarmConfig:
    """
    All inputs needed to run a savings simulation for one farm.
    This is the API surface — everything else is derived from this.
    """
    # Identity
    farm_name: str = "Demo Farm"

    # Location & utility
    utility: str = "PG&E"          # "PG&E", "SCE", "SDG&E"
    tariff_key: str = "PG&E:AG-B"  # Key from tariff registry
    climate_region: str = "central_valley"
    lat: float = 36.75             # Default: Fresno area
    lon: float = -119.77

    # Crop & irrigation
    crop_name: str = "almond"
    irrigation_type: str = "drip"
    area_acres: float = 200.0

    # Pump system
    pump_kw: float = 75.0          # Nameplate kW
    total_dynamic_head_ft: Optional[float] = None   # If None, uses crop default
    pump_efficiency: float = 0.68  # Wire-to-water
    motor_efficiency: float = 0.92

    # Solar (optional)
    has_solar: bool = False
    solar_kw_dc: float = 0.0
    solar_tilt_deg: Optional[float] = None
    solar_azimuth_deg: float = 180.0
    solar_array_type: int = 1      # 1=ground fixed, 2=1-axis tracker
    solar_losses_pct: float = 14.0

    # NEM program
    nem_program: str = "NBT"       # "NEM2" or "NBT"
    nem_vintage_year: int = 2025   # For NBT: year of PTO

    # Simulation settings
    year: int = 2024
    store_hourly: bool = False     # True to include 8760 arrays in output (large)


def run_simulation(config: FarmConfig) -> SavingsReport:
    """
    Run the complete SunBreak savings simulation for a farm configuration.

    Steps:
      1. Load tariff from registry
      2. Build baseline load profile (crop ET × irrigation archetype × baseline schedule)
      3. Generate solar profile (if solar present)
      4. Build export schedule (NEM2 or NBT)
      5. Build hourly rate array
      6. Run baseline simulation (bill without SunBreak)
      7. Build optimized load profile (SunBreak scheduler)
      8. Run optimized simulation (bill with SunBreak)
      9. Return SavingsReport with full comparison

    Returns:
        SavingsReport with .summary() method for quick output
    """
    # ── 1. Tariff ──────────────────────────────────────────────────────────
    tariff = REGISTRY.get(config.tariff_key)

    # ── 2. Baseline load profile ──────────────────────────────────────────
    print(f"  Building load profile: {config.crop_name} / {config.irrigation_type} / "
          f"{config.area_acres} acres / {config.pump_kw} kW pump...")
    baseline_load = build_baseline_load_profile(
        crop_name=config.crop_name,
        irrigation_type=config.irrigation_type,
        climate_region=config.climate_region,
        area_acres=config.area_acres,
        pump_kw=config.pump_kw,
        total_dynamic_head_ft=config.total_dynamic_head_ft,
        pump_efficiency=config.pump_efficiency,
        motor_efficiency=config.motor_efficiency,
        year=config.year,
    )

    # ── 3. Solar profile ──────────────────────────────────────────────────
    if config.has_solar and config.solar_kw_dc > 0:
        print(f"  Generating solar profile: {config.solar_kw_dc} kW DC...")
        pv = PVSystem(
            system_kw_dc=config.solar_kw_dc,
            lat=config.lat,
            lon=config.lon,
            tilt_deg=config.solar_tilt_deg,
            azimuth_deg=config.solar_azimuth_deg,
            array_type=config.solar_array_type,
            losses_pct=config.solar_losses_pct,
        )
        solar_8760 = generate_solar_profile(pv, config.climate_region, config.year)
    else:
        solar_8760 = [0.0] * 8760

    # ── 4. Export schedule ─────────────────────────────────────────────────
    if config.has_solar and config.nem_program == "NEM2":
        export_schedule = build_nem2_export_schedule(tariff)
    elif config.has_solar and config.nem_program == "NBT":
        export_schedule = build_nbt_export_schedule(tariff.utility, config.nem_vintage_year)
    else:
        export_schedule = None

    # ── 5. Hourly rate array for optimizer ────────────────────────────────
    import datetime
    start = datetime.datetime(config.year, 1, 1)
    hourly_rates = [tariff.energy_rate_at(start + datetime.timedelta(hours=h))
                    for h in range(8760)]
    export_rates = [export_schedule.rate_at_hour(h) if export_schedule else 0.04
                    for h in range(8760)]

    # ── 6. Baseline simulation ─────────────────────────────────────────────
    print(f"  Running baseline simulation ({tariff.schedule})...")
    baseline_result = simulate(
        load_8760=baseline_load,
        solar_8760=solar_8760,
        tariff=tariff,
        export_schedule=export_schedule,
        scenario="baseline",
        year=config.year,
        store_hourly=config.store_hourly,
    )

    # ── 7. Optimized load profile ─────────────────────────────────────────
    print(f"  Running SunBreak optimizer...")
    optimized_load = build_optimized_load_profile(
        baseline_load=baseline_load,
        system_name=config.irrigation_type,
        hourly_rates_8760=hourly_rates,
        solar_8760=solar_8760,
        export_rates_8760=export_rates,
        pump_kw=config.pump_kw,
        area_acres=config.area_acres,
        crop_name=config.crop_name,
        climate_region=config.climate_region,
        year=config.year,
    )

    # ── 8. Optimized simulation ───────────────────────────────────────────
    print(f"  Running optimized simulation...")
    optimized_result = simulate(
        load_8760=optimized_load,
        solar_8760=solar_8760,
        tariff=tariff,
        export_schedule=export_schedule,
        scenario="optimized",
        year=config.year,
        store_hourly=config.store_hourly,
    )

    # ── 9. Return savings report ──────────────────────────────────────────
    return SavingsReport(
        baseline=baseline_result,
        optimized=optimized_result,
        tariff=tariff,
        farm_name=config.farm_name,
        crop_name=config.crop_name,
        irrigation_type=config.irrigation_type,
        area_acres=config.area_acres,
        pump_kw=config.pump_kw,
        solar_kw=config.solar_kw_dc,
    )
