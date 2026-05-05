# tariffs/sce.py
"""
SCE Agricultural & Pumping Rate Schedules — effective 2026.
Source: SCE Rate Schedule TOU-PA-2 and TOU-PA-3 (CPUC-approved tariffs).

TOU-PA-2: Small to Medium Agricultural & Pumping (demand < 200 kW) — mandatory
TOU-PA-3: Large Agricultural & Pumping (200–500 kW demand)

Season definitions:
  Summer: June 1 – September 30
  Winter: October 1 – May 31

Peak hours (Option D, standard): 4:00 PM – 9:00 PM weekdays (excluding holidays)
Mid-peak: 8:00 AM – 4:00 PM weekdays; 8:00 AM – 9:00 PM weekends (approx)
Off-peak: all other hours

Option D-5TO8: Peak is 5:00 PM – 8:00 PM (narrower window, lower demand charge exposure)
Option E: No time-related demand charge, higher FRD, flat energy premium

Wind machine credit available for winter-only frost-protection accounts.
"""

from .models import TOUPeriod, Tariff, NEM_PROGRAM

WEEKDAYS = {0, 1, 2, 3, 4}
WEEKENDS = {5, 6}
ALL_DAYS = {0, 1, 2, 3, 4, 5, 6}
SUMMER_MONTHS = {6, 7, 8, 9}
WINTER_MONTHS = {1, 2, 3, 4, 5, 10, 11, 12}
ALL_MONTHS = set(range(1, 13))

SCE_NBC = 0.022  # Non-bypassable charges approx $/kWh

# Option D standard peak window: 4pm–9pm
PEAK_HOURS_D = {16, 17, 18, 19, 20}
# Option D-5TO8 peak window: 5pm–8pm
PEAK_HOURS_5TO8 = {17, 18, 19}
# Mid-peak: 8am–4pm weekdays (summer)
MID_PEAK_HOURS = {8, 9, 10, 11, 12, 13, 14, 15}
OFF_PEAK_HOURS_D = set(range(24)) - PEAK_HOURS_D - MID_PEAK_HOURS


# ─────────────────────────────────────────────────────────────────────────────
# TOU-PA-2, Option D  (most common for farms < 200 kW)
# Has both FRD and TRD on peak/mid-peak windows
# ─────────────────────────────────────────────────────────────────────────────
TOU_PA2_D = Tariff(
    utility="SCE",
    schedule="TOU-PA-2-D",
    description="Agricultural & Pumping Small-Med, Option D (4–9 PM peak)",
    customer_charge=12.40,
    facilities_demand_rate=6.20,       # $/kW/month FRD on monthly max
    summer_peak_demand_rate=0.0,
    default_energy_rate=0.155,
    periods=[
        # Summer peak (weekdays only)
        TOUPeriod("summer_peak", SUMMER_MONTHS, WEEKDAYS, PEAK_HOURS_D,
                  energy_rate=0.3280, demand_rate_trd=11.80),
        # Summer mid-peak (weekdays)
        TOUPeriod("summer_mid_peak", SUMMER_MONTHS, WEEKDAYS, MID_PEAK_HOURS,
                  energy_rate=0.2010, demand_rate_trd=2.40),
        # Summer off-peak
        TOUPeriod("summer_off_peak", SUMMER_MONTHS, ALL_DAYS,
                  OFF_PEAK_HOURS_D | set(range(24)) - PEAK_HOURS_D,
                  energy_rate=0.1420),
        # Winter peak
        TOUPeriod("winter_peak", WINTER_MONTHS, WEEKDAYS, PEAK_HOURS_D,
                  energy_rate=0.2180, demand_rate_trd=3.60),
        # Winter mid-peak
        TOUPeriod("winter_mid_peak", WINTER_MONTHS, WEEKDAYS, MID_PEAK_HOURS,
                  energy_rate=0.1650),
        # Winter off-peak
        TOUPeriod("winter_off_peak", WINTER_MONTHS, ALL_DAYS,
                  set(range(24)) - PEAK_HOURS_D - MID_PEAK_HOURS,
                  energy_rate=0.1320),
    ],
    fixed_adders=SCE_NBC,
    min_demand_kw=0,
    max_demand_kw=200,
)

# ─────────────────────────────────────────────────────────────────────────────
# TOU-PA-2, Option D-5TO8  (narrower peak window, good for farms with flexible
# early evening irrigation — pumps can run until 5pm without peak charge)
# ─────────────────────────────────────────────────────────────────────────────
TOU_PA2_D_5TO8 = Tariff(
    utility="SCE",
    schedule="TOU-PA-2-D-5TO8",
    description="Agricultural & Pumping Small-Med, Option D 5–8 PM peak",
    customer_charge=12.40,
    facilities_demand_rate=6.20,
    summer_peak_demand_rate=0.0,
    default_energy_rate=0.152,
    periods=[
        TOUPeriod("summer_peak", SUMMER_MONTHS, WEEKDAYS, PEAK_HOURS_5TO8,
                  energy_rate=0.3510, demand_rate_trd=14.20),
        TOUPeriod("summer_mid_peak", SUMMER_MONTHS, WEEKDAYS,
                  set(range(8, 17)) - PEAK_HOURS_5TO8, energy_rate=0.2050),
        TOUPeriod("summer_off_peak", SUMMER_MONTHS, ALL_DAYS,
                  set(range(24)) - PEAK_HOURS_5TO8 - set(range(8, 17)),
                  energy_rate=0.1380),
        TOUPeriod("winter_peak", WINTER_MONTHS, WEEKDAYS, PEAK_HOURS_5TO8,
                  energy_rate=0.2250, demand_rate_trd=4.10),
        TOUPeriod("winter_off_peak", WINTER_MONTHS, ALL_DAYS,
                  set(range(24)) - PEAK_HOURS_5TO8, energy_rate=0.1310),
    ],
    fixed_adders=SCE_NBC,
    min_demand_kw=0,
    max_demand_kw=200,
)

# ─────────────────────────────────────────────────────────────────────────────
# TOU-PA-2, Option E  (higher FRD, no TRD — good for farms that can't avoid
# peak because of crop/labor needs; demand charge is predictable)
# ─────────────────────────────────────────────────────────────────────────────
TOU_PA2_E = Tariff(
    utility="SCE",
    schedule="TOU-PA-2-E",
    description="Agricultural & Pumping Small-Med, Option E (FRD only, no TRD)",
    customer_charge=12.40,
    facilities_demand_rate=14.80,      # Higher FRD; no TRD
    summer_peak_demand_rate=0.0,
    default_energy_rate=0.148,
    periods=[
        TOUPeriod("summer_peak", SUMMER_MONTHS, WEEKDAYS, PEAK_HOURS_D,
                  energy_rate=0.2740),  # No TRD
        TOUPeriod("summer_off_peak", SUMMER_MONTHS, ALL_DAYS,
                  set(range(24)) - PEAK_HOURS_D, energy_rate=0.1450),
        TOUPeriod("winter_peak", WINTER_MONTHS, WEEKDAYS, PEAK_HOURS_D,
                  energy_rate=0.1890),
        TOUPeriod("winter_off_peak", WINTER_MONTHS, ALL_DAYS,
                  set(range(24)) - PEAK_HOURS_D, energy_rate=0.1320),
    ],
    fixed_adders=SCE_NBC,
    min_demand_kw=0,
    max_demand_kw=200,
)

# ─────────────────────────────────────────────────────────────────────────────
# TOU-PA-3, Option D  (large ag 200–500 kW)
# Similar structure to PA-2-D but CPP default enrollment; higher base rates
# ─────────────────────────────────────────────────────────────────────────────
TOU_PA3_D = Tariff(
    utility="SCE",
    schedule="TOU-PA-3-D",
    description="Agricultural & Pumping Large (200–500 kW), Option D",
    customer_charge=35.90,
    facilities_demand_rate=7.50,
    summer_peak_demand_rate=0.0,
    default_energy_rate=0.162,
    periods=[
        TOUPeriod("summer_peak", SUMMER_MONTHS, WEEKDAYS, PEAK_HOURS_D,
                  energy_rate=0.3540, demand_rate_trd=13.20),
        TOUPeriod("summer_mid_peak", SUMMER_MONTHS, WEEKDAYS, MID_PEAK_HOURS,
                  energy_rate=0.2140, demand_rate_trd=2.80),
        TOUPeriod("summer_off_peak", SUMMER_MONTHS, ALL_DAYS,
                  set(range(24)) - PEAK_HOURS_D - MID_PEAK_HOURS,
                  energy_rate=0.1480),
        TOUPeriod("winter_peak", WINTER_MONTHS, WEEKDAYS, PEAK_HOURS_D,
                  energy_rate=0.2320, demand_rate_trd=4.20),
        TOUPeriod("winter_off_peak", WINTER_MONTHS, ALL_DAYS,
                  set(range(24)) - PEAK_HOURS_D, energy_rate=0.1380),
    ],
    fixed_adders=SCE_NBC,
    min_demand_kw=200,
    max_demand_kw=500,
)

# ─────────────────────────────────────────────────────────────────────────────
# TOU-PA-3, Option E  (large ag, FRD only)
# ─────────────────────────────────────────────────────────────────────────────
TOU_PA3_E = Tariff(
    utility="SCE",
    schedule="TOU-PA-3-E",
    description="Agricultural & Pumping Large (200–500 kW), Option E (FRD only)",
    customer_charge=35.90,
    facilities_demand_rate=17.20,
    summer_peak_demand_rate=0.0,
    default_energy_rate=0.158,
    periods=[
        TOUPeriod("summer_peak", SUMMER_MONTHS, WEEKDAYS, PEAK_HOURS_D,
                  energy_rate=0.2950),
        TOUPeriod("summer_off_peak", SUMMER_MONTHS, ALL_DAYS,
                  set(range(24)) - PEAK_HOURS_D, energy_rate=0.1520),
        TOUPeriod("winter_peak", WINTER_MONTHS, WEEKDAYS, PEAK_HOURS_D,
                  energy_rate=0.2010),
        TOUPeriod("winter_off_peak", WINTER_MONTHS, ALL_DAYS,
                  set(range(24)) - PEAK_HOURS_D, energy_rate=0.1410),
    ],
    fixed_adders=SCE_NBC,
    min_demand_kw=200,
    max_demand_kw=500,
)


SCE_TARIFFS = {
    "SCE:TOU-PA-2-D": TOU_PA2_D,
    "SCE:TOU-PA-2-D-5TO8": TOU_PA2_D_5TO8,
    "SCE:TOU-PA-2-E": TOU_PA2_E,
    "SCE:TOU-PA-3-D": TOU_PA3_D,
    "SCE:TOU-PA-3-E": TOU_PA3_E,
}
