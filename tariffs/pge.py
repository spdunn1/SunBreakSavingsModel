# tariffs/pge.py
"""
PG&E Agricultural Rate Schedules — effective Jan 1, 2026.
Source: PG&E Electric Schedule AG (Cal. P.U.C. Sheet No. 60613-E)
        and Schedule AG-1 for legacy customers.

TOU Periods (post-2021 mandatory for non-grandfathered):
  Summer (Jun–Sep):
    Peak        : 5:00 PM – 8:00 PM, weekdays
    Off-Peak    : all other hours
  Winter (Oct–May):
    Peak        : 5:00 PM – 8:00 PM, weekdays  (lower rate)
    Off-Peak    : all other hours

Rates include bundled generation + delivery. Non-bypassable charges
(public purpose, nuclear decommissioning, DWR bond) ~$0.013/kWh added
as fixed_adders (approximate 2026 values).

All demand charges based on 15-minute interval maximum.
"""

from .models import TOUPeriod, Tariff, NEM_PROGRAM

WEEKDAYS = {0, 1, 2, 3, 4}
ALL_DAYS = {0, 1, 2, 3, 4, 5, 6}
SUMMER_MONTHS = {6, 7, 8, 9}
WINTER_MONTHS = {1, 2, 3, 4, 5, 10, 11, 12}
ALL_MONTHS = set(range(1, 13))
PEAK_HOURS = {17, 18, 19}          # 5–8 PM
OFF_PEAK_HOURS = set(range(24)) - PEAK_HOURS

# Non-bypassable charges (NBC): ~$0.013/kWh
# PCIA (Power Charge Indifference Adjustment): varies ~$0.02–0.04/kWh for bundled
# Using a blended fixed adder of $0.025/kWh as approximation for bundled service
PGE_NBC = 0.025


def _pge_summer_off_peak(rate: float) -> TOUPeriod:
    return TOUPeriod("summer_off_peak", SUMMER_MONTHS, ALL_DAYS, OFF_PEAK_HOURS, rate)


def _pge_summer_peak(rate: float, trd: float = 0.0) -> TOUPeriod:
    return TOUPeriod("summer_peak", SUMMER_MONTHS, WEEKDAYS, PEAK_HOURS, rate, trd)


def _pge_winter_off_peak(rate: float) -> TOUPeriod:
    return TOUPeriod("winter_off_peak", WINTER_MONTHS, ALL_DAYS, OFF_PEAK_HOURS, rate)


def _pge_winter_peak(rate: float) -> TOUPeriod:
    return TOUPeriod("winter_peak", WINTER_MONTHS, WEEKDAYS, PEAK_HOURS, rate)


# ─────────────────────────────────────────────────────────────────────────────
# AG-A1: Small Agricultural, No Demand Charge
# Eligible: < 35 kW average demand, no demand metering
# ─────────────────────────────────────────────────────────────────────────────
AG_A1 = Tariff(
    utility="PG&E",
    schedule="AG-A1",
    description="Small Agricultural, No Demand Charge",
    customer_charge=10.50,          # $/month
    facilities_demand_rate=0.0,
    summer_peak_demand_rate=0.0,
    default_energy_rate=0.18,
    periods=[
        _pge_summer_peak(0.3650),
        _pge_summer_off_peak(0.1820),
        _pge_winter_peak(0.2490),
        _pge_winter_off_peak(0.1680),
    ],
    fixed_adders=PGE_NBC,
    min_demand_kw=0,
    max_demand_kw=35,
)

# ─────────────────────────────────────────────────────────────────────────────
# AG-A2: Small Agricultural, With Demand Charge
# Eligible: < 35 kW avg demand, customer elects demand metering
# ─────────────────────────────────────────────────────────────────────────────
AG_A2 = Tariff(
    utility="PG&E",
    schedule="AG-A2",
    description="Small Agricultural, With Demand Charge",
    customer_charge=10.50,
    facilities_demand_rate=8.40,    # $/kW/month on monthly max
    summer_peak_demand_rate=0.0,
    default_energy_rate=0.16,
    periods=[
        _pge_summer_peak(0.3120),
        _pge_summer_off_peak(0.1560),
        _pge_winter_peak(0.2130),
        _pge_winter_off_peak(0.1440),
    ],
    fixed_adders=PGE_NBC,
    min_demand_kw=0,
    max_demand_kw=35,
)

# ─────────────────────────────────────────────────────────────────────────────
# AG-B: Medium-Large Agricultural, With Demand Charge
# Eligible: ≥ 35 kW registered demand
# Most common rate for mid-sized farms with pumps 50–200 hp
# ─────────────────────────────────────────────────────────────────────────────
AG_B = Tariff(
    utility="PG&E",
    schedule="AG-B",
    description="Medium-Large Agricultural, With Demand Charge",
    customer_charge=22.75,
    facilities_demand_rate=10.25,   # $/kW/month FRD on monthly peak
    summer_peak_demand_rate=0.0,
    default_energy_rate=0.14,
    periods=[
        _pge_summer_peak(0.2980, trd=3.50),   # TRD on summer peak window
        _pge_summer_off_peak(0.1410),
        _pge_winter_peak(0.1970),
        _pge_winter_off_peak(0.1310),
    ],
    fixed_adders=PGE_NBC,
    min_demand_kw=35,
    max_demand_kw=499,
)

# ─────────────────────────────────────────────────────────────────────────────
# AG-C: Large Agricultural, Peak + Non-Peak Demand Charges
# Has both FRD + summer peak demand charge; demand charge limiter $0.50/kWh cap
# Eligible: ≥ 35 kW registered demand (large farms, well systems)
# ─────────────────────────────────────────────────────────────────────────────
AG_C = Tariff(
    utility="PG&E",
    schedule="AG-C",
    description="Large Agricultural, Summer Peak Demand + Demand Limiter",
    customer_charge=22.75,
    facilities_demand_rate=7.80,    # $/kW/month FRD
    summer_peak_demand_rate=15.40,  # $/kW extra on summer peak window max kW
    default_energy_rate=0.13,
    periods=[
        _pge_summer_peak(0.2640, trd=0.0),    # TRD captured in summer_peak_demand_rate
        _pge_summer_off_peak(0.1280),
        _pge_winter_peak(0.1780),
        _pge_winter_off_peak(0.1190),
    ],
    fixed_adders=PGE_NBC,
    min_demand_kw=35,
    max_demand_kw=float("inf"),
)

# ─────────────────────────────────────────────────────────────────────────────
# AG-1 (Legacy): Pre-2021 TOU periods, grandfathered solar customers only
# Kept for existing customers; different peak window (noon–6pm historically)
# Approximate — verify against actual grandfathered customer agreement
# ─────────────────────────────────────────────────────────────────────────────
_LEGACY_PEAK_HOURS = {12, 13, 14, 15, 16, 17}
AG_1_LEGACY = Tariff(
    utility="PG&E",
    schedule="AG-1-Legacy",
    description="Legacy Small Agricultural (Pre-2021 TOU, grandfathered NEM2)",
    customer_charge=10.50,
    facilities_demand_rate=8.10,
    summer_peak_demand_rate=0.0,
    default_energy_rate=0.17,
    periods=[
        TOUPeriod("summer_peak", SUMMER_MONTHS, WEEKDAYS, _LEGACY_PEAK_HOURS, 0.2950),
        TOUPeriod("summer_off_peak", SUMMER_MONTHS, ALL_DAYS,
                  set(range(24)) - _LEGACY_PEAK_HOURS, 0.1650),
        TOUPeriod("winter_peak", WINTER_MONTHS, WEEKDAYS, _LEGACY_PEAK_HOURS, 0.2010),
        TOUPeriod("winter_off_peak", WINTER_MONTHS, ALL_DAYS,
                  set(range(24)) - _LEGACY_PEAK_HOURS, 0.1520),
    ],
    fixed_adders=PGE_NBC,
    nem_program=NEM_PROGRAM.NEM2,  # Legacy customers are on NEM 2.0
)

# ─────────────────────────────────────────────────────────────────────────────
# AG-B Flex Option 1: Off-peak days are Wednesday & Thursday
# Suitable for farms that can concentrate heavy irrigation mid-week
# ─────────────────────────────────────────────────────────────────────────────
AG_B_FLEX1 = Tariff(
    utility="PG&E",
    schedule="AG-B-Flex1",
    description="AG-B Flex: Off-peak Wed/Thu",
    customer_charge=22.75,
    facilities_demand_rate=10.25,
    summer_peak_demand_rate=0.0,
    default_energy_rate=0.14,
    periods=[
        # Wed(2) and Thu(3) are all off-peak regardless of hour
        TOUPeriod("flex_offpeak_days", ALL_MONTHS, {2, 3}, set(range(24)), 0.1280),
        _pge_summer_peak(0.2980, trd=3.50),
        _pge_summer_off_peak(0.1410),
        _pge_winter_peak(0.1970),
        _pge_winter_off_peak(0.1310),
    ],
    fixed_adders=PGE_NBC,
    min_demand_kw=35,
)


PGE_TARIFFS = {
    "PG&E:AG-A1": AG_A1,
    "PG&E:AG-A2": AG_A2,
    "PG&E:AG-B": AG_B,
    "PG&E:AG-C": AG_C,
    "PG&E:AG-1-Legacy": AG_1_LEGACY,
    "PG&E:AG-B-Flex1": AG_B_FLEX1,
}
