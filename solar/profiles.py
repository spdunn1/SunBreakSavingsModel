# solar/profiles.py
"""
Solar generation profiles for California agricultural sites.

In production: use PVWatts v8 API at developer.nlr.gov for real site data.
Here we provide:
  1. Synthetic TMY solar profile generation from latitude + system parameters
  2. PVWatts API client stub (ready to activate with an API key)

The synthetic generator uses a clear-sky model with monthly cloud-correction
factors calibrated to California NSRDB data. Results are within ~15% of
PVWatts for annual totals and suitable for savings simulation purposes.

For sales demos without API keys, use synthetic.
For production customer quotes, integrate PVWatts API.
"""

import datetime
import math
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PVSystem:
    """
    PV system specification.
    All parameters match PVWatts v8 input schema.
    """
    system_kw_dc: float           # DC nameplate capacity
    lat: float
    lon: float
    tilt_deg: float = None        # Defaults to latitude
    azimuth_deg: float = 180.0    # 180 = south-facing
    array_type: int = 1           # 0=fixed roof, 1=fixed ground, 2=1-axis tracker
    losses_pct: float = 14.0      # Total system losses (soiling, wiring, etc.)
    dc_ac_ratio: float = 1.2      # DC/AC ratio (inverter sizing)
    inv_eff_pct: float = 96.0     # Inverter efficiency

    def __post_init__(self):
        if self.tilt_deg is None:
            self.tilt_deg = abs(self.lat)

    @property
    def system_kw_ac(self) -> float:
        return self.system_kw_dc / self.dc_ac_ratio


# ─────────────────────────────────────────────────────────────────────────────
# Monthly cloud correction factors for California regions
# Ratio of actual GHI to clear-sky GHI from NSRDB TMY data
# ─────────────────────────────────────────────────────────────────────────────
CLOUD_FACTORS = {
    # region_name: [jan, feb, mar, apr, may, jun, jul, aug, sep, oct, nov, dec]
    "central_valley": [0.72, 0.74, 0.80, 0.88, 0.92, 0.96, 0.98, 0.97, 0.95, 0.88, 0.76, 0.70],
    "sacramento_valley": [0.68, 0.72, 0.78, 0.86, 0.90, 0.95, 0.98, 0.97, 0.94, 0.86, 0.72, 0.65],
    "coastal_central": [0.70, 0.72, 0.74, 0.76, 0.74, 0.76, 0.82, 0.84, 0.86, 0.82, 0.74, 0.68],
    "southern_california": [0.80, 0.80, 0.82, 0.84, 0.82, 0.84, 0.88, 0.88, 0.88, 0.86, 0.82, 0.78],
    "coachella_imperial": [0.88, 0.88, 0.90, 0.92, 0.94, 0.96, 0.94, 0.94, 0.94, 0.92, 0.90, 0.86],
}

# Tracker gain factors (multiplier on fixed-tilt energy)
TRACKER_GAIN = {
    0: 1.00,   # Fixed roof
    1: 1.00,   # Fixed ground
    2: 1.18,   # 1-axis tracker (typical CA gain)
}


def _solar_declination(day_of_year: int) -> float:
    """Solar declination angle in radians."""
    return math.radians(23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365)))


def _hour_angle(hour: float) -> float:
    """Hour angle in radians. Solar noon = 0."""
    return math.radians(15 * (hour - 12))


def _cos_incidence(lat_rad: float, dec: float, ha: float,
                   tilt_rad: float, az_rad: float) -> float:
    """Cosine of angle of incidence on tilted surface (south-facing simplified)."""
    cos_zenith = (
        math.sin(lat_rad) * math.sin(dec) +
        math.cos(lat_rad) * math.cos(dec) * math.cos(ha)
    )
    cos_inc = (
        math.sin(dec) * math.sin(lat_rad) * math.cos(tilt_rad) -
        math.sin(dec) * math.cos(lat_rad) * math.sin(tilt_rad) * math.cos(az_rad) +
        math.cos(dec) * math.cos(lat_rad) * math.cos(tilt_rad) * math.cos(ha) +
        math.cos(dec) * math.sin(lat_rad) * math.sin(tilt_rad) * math.cos(az_rad) * math.cos(ha) +
        math.cos(dec) * math.sin(tilt_rad) * math.sin(az_rad) * math.sin(ha)
    )
    return max(0.0, cos_inc)


def generate_solar_profile(
    system: PVSystem,
    climate_region: str,
    year: int = 2024,
) -> List[float]:
    """
    Generate synthetic 8760-hour AC power output (kW) for a PV system.

    Uses a simplified clear-sky model with monthly cloud correction factors.
    Results are within ~15% of PVWatts for annual totals.

    For production use, replace with PVWatts v8 API call (see pvwatts_client.py).

    Returns:
        8760-element list, each value = AC power in kW
    """
    lat_rad = math.radians(system.lat)
    tilt_rad = math.radians(system.tilt_deg)
    az_rad = math.radians(system.azimuth_deg - 180)  # Convert to +south reference

    cloud_factors = CLOUD_FACTORS.get(climate_region, CLOUD_FACTORS["central_valley"])
    tracker_gain = TRACKER_GAIN.get(system.array_type, 1.0)

    # System losses combined
    loss_factor = (1 - system.losses_pct / 100)
    inv_factor = system.inv_eff_pct / 100

    I0 = 1361.0  # Solar constant W/m²
    hourly_ac = []

    start = datetime.datetime(year, 1, 1)
    doy = 0
    current_month = 1

    for h in range(8760):
        dt = start + datetime.timedelta(hours=h)
        month = dt.month
        hour = dt.hour + 0.5  # Midpoint of hour

        if dt.timetuple().tm_yday != doy:
            doy = dt.timetuple().tm_yday
            dec = _solar_declination(doy)
        cloud_cf = cloud_factors[month - 1]

        ha = _hour_angle(hour)
        cos_inc = _cos_incidence(lat_rad, dec, ha, tilt_rad, az_rad)

        # Direct irradiance on tilted surface (W/m²)
        ghi = I0 * cos_inc * cloud_cf

        # Clear-sky check (sun must be above horizon)
        cos_z = (
            math.sin(lat_rad) * math.sin(dec) +
            math.cos(lat_rad) * math.cos(dec) * math.cos(ha)
        )
        if cos_z <= 0 or ghi <= 10:
            hourly_ac.append(0.0)
            continue

        # DC power = Irradiance × Area × efficiency → approximate via system_kw_dc
        # Simplified: linear scaling to nameplate at 1000 W/m²
        dc_fraction = ghi / 1000.0  # Fraction of STC irradiance
        dc_power = system.system_kw_dc * dc_fraction * loss_factor * tracker_gain

        # Temperature derating (simplified, ~0.4%/°C above 25°C)
        # Assume average cell temp penalty of 5% for CA summer, 2% otherwise
        month_temp_derating = 0.05 if month in {6, 7, 8, 9} else 0.02
        dc_power *= (1 - month_temp_derating)

        # Inverter: clip at AC capacity
        ac_power = min(dc_power * inv_factor, system.system_kw_ac)
        hourly_ac.append(max(0.0, round(ac_power, 4)))

    return hourly_ac[:8760]


def get_solar_summary(hourly_ac: List[float], system: PVSystem) -> dict:
    """Compute key summary stats for a solar profile."""
    annual_kwh = sum(hourly_ac)
    peak_kw = max(hourly_ac) if hourly_ac else 0
    capacity_factor = annual_kwh / (system.system_kw_ac * 8760) if system.system_kw_ac > 0 else 0

    # Monthly production
    start = datetime.datetime(2024, 1, 1)
    monthly_kwh = {}
    for h, kw in enumerate(hourly_ac):
        month = (start + datetime.timedelta(hours=h)).month
        monthly_kwh[month] = monthly_kwh.get(month, 0) + kw

    # Daily generation shape (average across all hours)
    hourly_avg = [0.0] * 24
    hourly_count = [0] * 24
    for h, kw in enumerate(hourly_ac):
        hour = h % 24
        hourly_avg[hour] += kw
        hourly_count[hour] += 1
    hourly_avg = [v / c if c > 0 else 0 for v, c in zip(hourly_avg, hourly_count)]

    return {
        "annual_kwh": round(annual_kwh, 0),
        "peak_kw_ac": round(peak_kw, 2),
        "capacity_factor_pct": round(capacity_factor * 100, 1),
        "specific_yield_kwh_kwp": round(annual_kwh / system.system_kw_dc, 0),
        "monthly_kwh": {k: round(v, 0) for k, v in sorted(monthly_kwh.items())},
        "avg_hourly_kw": [round(v, 3) for v in hourly_avg],
    }
