# tariffs/sdge.py
"""
SDG&E Agricultural Rate Schedules — effective 2026.
Source: SDG&E Electric Schedule AL-TOU and PA rates.

SDG&E serves agricultural customers in San Diego and southern Imperial counties.
Agricultural load is much smaller than PG&E/SCE territory — mostly avocado,
citrus, nursery, small vineyards, strawberries.

Key schedules:
  AL-TOU   : Agricultural & Lighting, Time-of-Use (small accounts)
  TOU-PA   : Agricultural & Pumping (pumping-heavy accounts)
  ALTOU-P  : Agricultural Large TOU with Pumping provision

SDG&E has highest base rates of the three CA IOUs due to lack of hydro/nuclear.
Summer is May 1 – October 31 (longer than PG&E/SCE).
Peak: 4:00 PM – 9:00 PM (all days in summer, weekdays in winter).

SDG&E does not have a separate "small ag no demand" option comparable to PG&E AG-A1.
All accounts > 20 kW have demand charges.

Rates shown are approximate 2026 bundled rates — SDG&E updates quarterly.
"""

from .models import TOUPeriod, Tariff, NEM_PROGRAM

WEEKDAYS = {0, 1, 2, 3, 4}
ALL_DAYS = {0, 1, 2, 3, 4, 5, 6}
# SDG&E summer: May 1 – Oct 31 (longer window!)
SUMMER_MONTHS = {5, 6, 7, 8, 9, 10}
WINTER_MONTHS = {1, 2, 3, 4, 11, 12}
ALL_MONTHS = set(range(1, 13))

SDGE_NBC = 0.028  # Higher NBC than PG&E/SCE due to rate structure

# SDG&E peak window: 4–9 PM
PEAK_HOURS = {16, 17, 18, 19, 20}
# SDG&E super off-peak (March–May: 10am–2pm)
SUPER_OFFPEAK_HOURS = {10, 11, 12, 13}
SUPER_OFFPEAK_MONTHS = {3, 4, 5}
OFF_PEAK_HOURS = set(range(24)) - PEAK_HOURS


# ─────────────────────────────────────────────────────────────────────────────
# AL-TOU: Agricultural & Lighting, TOU  (small-medium ag accounts)
# No separate pumping provision — designed for diversified ag operations
# ─────────────────────────────────────────────────────────────────────────────
AL_TOU = Tariff(
    utility="SDG&E",
    schedule="AL-TOU",
    description="Agricultural & Lighting, TOU (small-medium ag)",
    customer_charge=18.60,
    facilities_demand_rate=9.80,        # $/kW/month
    summer_peak_demand_rate=8.50,       # Additional summer peak demand $/kW
    default_energy_rate=0.188,
    periods=[
        # Super off-peak (spring — important for SDG&E solar self-consumption)
        TOUPeriod("spring_super_offpeak", SUPER_OFFPEAK_MONTHS, ALL_DAYS,
                  SUPER_OFFPEAK_HOURS, energy_rate=0.0890),
        # Summer peak (all days — SDG&E is all-day including weekends during peak)
        TOUPeriod("summer_peak", SUMMER_MONTHS, ALL_DAYS, PEAK_HOURS,
                  energy_rate=0.4280, demand_rate_trd=15.40),
        # Summer off-peak
        TOUPeriod("summer_off_peak", SUMMER_MONTHS, ALL_DAYS,
                  OFF_PEAK_HOURS, energy_rate=0.1920),
        # Winter peak (weekdays only)
        TOUPeriod("winter_peak", WINTER_MONTHS, WEEKDAYS, PEAK_HOURS,
                  energy_rate=0.2840, demand_rate_trd=5.60),
        # Winter off-peak
        TOUPeriod("winter_off_peak", WINTER_MONTHS, ALL_DAYS,
                  OFF_PEAK_HOURS, energy_rate=0.1720),
    ],
    fixed_adders=SDGE_NBC,
    min_demand_kw=0,
    max_demand_kw=200,
)

# ─────────────────────────────────────────────────────────────────────────────
# TOU-PA: SDG&E Agricultural & Pumping TOU
# For accounts where irrigation pumping is primary load (≥ 70% pumping use)
# Slightly lower energy rates offset by higher demand charges than AL-TOU
# ─────────────────────────────────────────────────────────────────────────────
TOU_PA = Tariff(
    utility="SDG&E",
    schedule="TOU-PA",
    description="Agricultural & Pumping TOU (pumping-primary accounts)",
    customer_charge=18.60,
    facilities_demand_rate=11.20,
    summer_peak_demand_rate=9.80,
    default_energy_rate=0.175,
    periods=[
        TOUPeriod("spring_super_offpeak", SUPER_OFFPEAK_MONTHS, ALL_DAYS,
                  SUPER_OFFPEAK_HOURS, energy_rate=0.0780),
        TOUPeriod("summer_peak", SUMMER_MONTHS, ALL_DAYS, PEAK_HOURS,
                  energy_rate=0.3980, demand_rate_trd=17.80),
        TOUPeriod("summer_off_peak", SUMMER_MONTHS, ALL_DAYS,
                  OFF_PEAK_HOURS, energy_rate=0.1780),
        TOUPeriod("winter_peak", WINTER_MONTHS, WEEKDAYS, PEAK_HOURS,
                  energy_rate=0.2650, demand_rate_trd=6.20),
        TOUPeriod("winter_off_peak", WINTER_MONTHS, ALL_DAYS,
                  OFF_PEAK_HOURS, energy_rate=0.1590),
    ],
    fixed_adders=SDGE_NBC,
    min_demand_kw=0,
    max_demand_kw=500,
)

# ─────────────────────────────────────────────────────────────────────────────
# ALTOU-P: SDG&E Large Agricultural, TOU with Pumping (> 200 kW)
# For larger nursery/greenhouse operations, water districts, large orchards
# ─────────────────────────────────────────────────────────────────────────────
ALTOU_P = Tariff(
    utility="SDG&E",
    schedule="ALTOU-P",
    description="Large Agricultural TOU with Pumping (200+ kW)",
    customer_charge=45.20,
    facilities_demand_rate=13.50,
    summer_peak_demand_rate=11.20,
    default_energy_rate=0.168,
    periods=[
        TOUPeriod("spring_super_offpeak", SUPER_OFFPEAK_MONTHS, ALL_DAYS,
                  SUPER_OFFPEAK_HOURS, energy_rate=0.0720),
        TOUPeriod("summer_peak", SUMMER_MONTHS, ALL_DAYS, PEAK_HOURS,
                  energy_rate=0.3780, demand_rate_trd=19.50),
        TOUPeriod("summer_off_peak", SUMMER_MONTHS, ALL_DAYS,
                  OFF_PEAK_HOURS, energy_rate=0.1680),
        TOUPeriod("winter_peak", WINTER_MONTHS, WEEKDAYS, PEAK_HOURS,
                  energy_rate=0.2510, demand_rate_trd=7.10),
        TOUPeriod("winter_off_peak", WINTER_MONTHS, ALL_DAYS,
                  OFF_PEAK_HOURS, energy_rate=0.1510),
    ],
    fixed_adders=SDGE_NBC,
    min_demand_kw=200,
    max_demand_kw=float("inf"),
)


SDGE_TARIFFS = {
    "SDG&E:AL-TOU": AL_TOU,
    "SDG&E:TOU-PA": TOU_PA,
    "SDG&E:ALTOU-P": ALTOU_P,
}
