# tariffs/models.py
"""
Core data models for California agricultural utility tariff structures.
All rates are $/kWh or $/kW as noted. Rates reflect ~2026 published tariffs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class NEM_PROGRAM(str, Enum):
    NEM2 = "NEM2"          # Grandfathered, export at retail TOU rate
    NBT = "NBT"            # Net Billing Tariff (NEM 3.0), export at ACC avoided cost
    NONE = "NONE"          # No solar / no export program


@dataclass
class TOUPeriod:
    """
    Defines a single Time-of-Use pricing window.

    Example:
        TOUPeriod("summer_peak", months={6,7,8,9}, weekdays={0,1,2,3,4},
                  hours={17,18,19,20}, energy_rate=0.38)
    """
    name: str
    months: set            # 1-based: {1..12}
    weekdays: set          # 0=Monday .. 6=Sunday
    hours: set             # 0-23 (hour starting)
    energy_rate: float     # $/kWh total bundled
    demand_rate_trd: float = 0.0   # $/kW time-related demand charge for this window

    def matches(self, dt: datetime) -> bool:
        return (
            dt.month in self.months
            and dt.weekday() in self.weekdays
            and dt.hour in self.hours
        )


@dataclass
class Tariff:
    """
    Complete tariff specification for one utility rate schedule.

    Notes on demand charges:
    - facilities_demand_rate: applied to monthly peak kW regardless of time (FRD)
    - Each TOUPeriod can carry a demand_rate_trd for time-window-specific demand (TRD)
    - Summer-only demand (AG-C) handled via summer_peak_demand_rate
    """
    utility: str                         # "PG&E", "SCE", "SDG&E"
    schedule: str                        # "AG-B", "TOU-PA-2-D", "AL-TOU"
    description: str
    customer_charge: float               # $/month
    facilities_demand_rate: float        # $/kW/month on monthly max kW (FRD)
    periods: list                        # List[TOUPeriod], evaluated in order
    nem_program: NEM_PROGRAM = NEM_PROGRAM.NONE
    fixed_adders: float = 0.0           # $/kWh non-bypassable charges (NBC, PCIA, etc.)
    summer_peak_demand_rate: float = 0.0 # $/kW extra demand charge summers only (AG-C)
    default_energy_rate: float = 0.0    # fallback $/kWh if no period matches

    # Eligibility metadata
    min_demand_kw: float = 0.0
    max_demand_kw: float = float("inf")

    def energy_rate_at(self, dt: datetime) -> float:
        """Return total bundled energy rate $/kWh at a given datetime."""
        for period in self.periods:
            if period.matches(dt):
                return period.energy_rate + self.fixed_adders
        return self.default_energy_rate + self.fixed_adders

    def trd_rate_at(self, dt: datetime) -> float:
        """Return time-related demand rate $/kW for this timestep's TOU window."""
        for period in self.periods:
            if period.matches(dt):
                return period.demand_rate_trd
        return 0.0

    def is_summer(self, month: int) -> bool:
        """California ag summer season definition varies slightly by utility."""
        raise NotImplementedError("Implemented in subclasses or via utility field")

    def __str__(self):
        return f"{self.utility} {self.schedule} — {self.description}"


@dataclass
class ExportSchedule:
    """
    Hourly export compensation rates (8760 values).

    For NEM 2.0: export_rate[h] ≈ energy_rate_at(h)  (retail offset)
    For NBT    : export_rate[h] = ACC avoided cost values (~$0.04–0.08/kWh midday,
                                  higher during evening peak)
    """
    program: NEM_PROGRAM
    utility: str
    hourly_rates: list              # 8760 floats, $/kWh

    # NBT-specific
    vintage_year: Optional[int] = None   # PTO year locks rates for 9 years

    def rate_at_hour(self, hour_of_year: int) -> float:
        """hour_of_year: 0–8759"""
        return self.hourly_rates[hour_of_year % 8760]


# ─────────────────────────────────────────────────────────────────────────────
# Pre-built NEM 2.0 export schedule approximation (retail TOU offset)
# For NBT we generate synthetic ACC curves in registry.py
# ─────────────────────────────────────────────────────────────────────────────

def build_nem2_export_schedule(tariff: Tariff) -> ExportSchedule:
    """
    NEM 2.0 export credits ≈ retail rate at the time of export,
    minus non-bypassable charges (~$0.03/kWh).
    """
    import datetime as dt
    start = dt.datetime(2024, 1, 1)
    rates = []
    for h in range(8760):
        moment = start + dt.timedelta(hours=h)
        retail = tariff.energy_rate_at(moment)
        # Non-bypassable charges are NOT credited under NEM 2.0
        export = max(0, retail - 0.03)
        rates.append(export)
    return ExportSchedule(NEM_PROGRAM.NEM2, tariff.utility, rates)


def build_nbt_export_schedule(utility: str, vintage_year: int = 2025) -> ExportSchedule:
    """
    Synthetic NBT/NEM 3.0 ACC export schedule.
    Approximates the CPUC Avoided Cost Calculator hourly shape:
    - Midday (10am–3pm): ~$0.04–0.06/kWh (low, solar abundant)
    - Evening peak (5–9pm): ~$0.12–0.20/kWh (high, grid stress)
    - Summer evenings higher than winter
    - Values decline ~20%/yr for ACC Plus adder (captured in vintage year adjustment)

    In production: replace with actual CPUC ACC CSV download.
    """
    import datetime as dt
    import math

    start = dt.datetime(2024, 1, 1)
    vintage_factor = max(0.4, 1.0 - 0.20 * max(0, vintage_year - 2023))
    rates = []

    for h in range(8760):
        moment = start + dt.timedelta(hours=h)
        hour = moment.hour
        month = moment.month
        is_summer = month in {6, 7, 8, 9}

        # Base shape: low midday, higher evenings
        if 10 <= hour <= 14:
            base = 0.045  # midday solar surplus
        elif 17 <= hour <= 20:
            base = 0.18 if is_summer else 0.10  # evening ramp
        elif 6 <= hour <= 9:
            base = 0.08
        elif hour >= 21 or hour <= 5:
            base = 0.05
        else:
            base = 0.06

        # Summer premium
        summer_mult = 1.25 if is_summer else 1.0
        acc_rate = base * summer_mult * vintage_factor
        rates.append(round(acc_rate, 4))

    return ExportSchedule(NEM_PROGRAM.NBT, utility, rates, vintage_year=vintage_year)
