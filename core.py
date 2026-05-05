# simulator/core.py
"""
Core 8760-hour energy balance and bill calculator.

Runs both baseline and SunBreak-optimized scenarios and returns
the full savings breakdown:
  - Energy charge savings (TOU shifting)
  - Demand charge savings (peak kW reduction)
  - Solar self-consumption savings
  - Export credit changes
  - Net annual savings

All calculations use hourly resolution.
Demand charges use monthly-peak (simulates 15-min interval billing
with hourly data; actual demand charges may differ slightly).
"""

import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from tariffs.models import Tariff, ExportSchedule, NEM_PROGRAM


@dataclass
class SimulationResult:
    """Full output from one simulation run (baseline or optimized)."""
    scenario: str           # "baseline" or "optimized"

    # Annual totals
    total_energy_kwh: float
    total_grid_import_kwh: float
    total_solar_self_consumed_kwh: float
    total_solar_exported_kwh: float
    peak_kw_annual: float

    # Annual bill components
    annual_customer_charge: float
    annual_energy_charge: float
    annual_demand_charge_frd: float     # Facilities-related demand
    annual_demand_charge_trd: float     # Time-related demand
    annual_demand_charge_summer_peak: float
    annual_export_credit: float
    annual_total_bill: float

    # Monthly breakdown
    monthly_bills: Dict[int, dict] = field(default_factory=dict)
    monthly_kwh: Dict[int, float] = field(default_factory=dict)
    monthly_peak_kw: Dict[int, float] = field(default_factory=dict)
    monthly_solar_kwh: Dict[int, float] = field(default_factory=dict)

    # Hourly arrays (optional, for charting)
    hourly_load: Optional[List[float]] = None
    hourly_solar: Optional[List[float]] = None
    hourly_grid_import: Optional[List[float]] = None


@dataclass
class SavingsReport:
    """Delta between baseline and optimized simulation."""
    baseline: SimulationResult
    optimized: SimulationResult
    tariff: Tariff

    # Farm parameters
    farm_name: str = "Unnamed Farm"
    crop_name: str = ""
    irrigation_type: str = ""
    area_acres: float = 0
    pump_kw: float = 0
    solar_kw: float = 0

    @property
    def annual_bill_savings(self) -> float:
        return self.baseline.annual_total_bill - self.optimized.annual_total_bill

    @property
    def energy_charge_savings(self) -> float:
        return self.baseline.annual_energy_charge - self.optimized.annual_energy_charge

    @property
    def demand_charge_savings(self) -> float:
        return (
            (self.baseline.annual_demand_charge_frd - self.optimized.annual_demand_charge_frd) +
            (self.baseline.annual_demand_charge_trd - self.optimized.annual_demand_charge_trd) +
            (self.baseline.annual_demand_charge_summer_peak - self.optimized.annual_demand_charge_summer_peak)
        )

    @property
    def solar_savings(self) -> float:
        """Extra value from self-consumption (displacing grid imports)."""
        return (
            self.optimized.total_solar_self_consumed_kwh -
            self.baseline.total_solar_self_consumed_kwh
        ) * 0.25  # Approximate avg retail rate avoided

    @property
    def export_credit_change(self) -> float:
        """Change in export credits (may go down as more solar is self-consumed)."""
        return self.optimized.annual_export_credit - self.baseline.annual_export_credit

    @property
    def savings_pct(self) -> float:
        if self.baseline.annual_total_bill == 0:
            return 0.0
        return self.annual_bill_savings / self.baseline.annual_total_bill * 100

    @property
    def monthly_savings(self) -> Dict[int, float]:
        return {
            m: self.baseline.monthly_bills.get(m, {}).get("total", 0) -
               self.optimized.monthly_bills.get(m, {}).get("total", 0)
            for m in range(1, 13)
        }

    def summary(self) -> dict:
        return {
            "farm": self.farm_name,
            "utility": self.tariff.utility,
            "tariff": self.tariff.schedule,
            "crop": self.crop_name,
            "irrigation": self.irrigation_type,
            "area_acres": self.area_acres,
            "pump_kw": self.pump_kw,
            "solar_kw_dc": self.solar_kw,
            "baseline_annual_bill": round(self.baseline.annual_total_bill, 2),
            "optimized_annual_bill": round(self.optimized.annual_total_bill, 2),
            "annual_savings": round(self.annual_bill_savings, 2),
            "savings_pct": round(self.savings_pct, 1),
            "energy_charge_savings": round(self.energy_charge_savings, 2),
            "demand_charge_savings": round(self.demand_charge_savings, 2),
            "solar_self_consumption_savings": round(self.solar_savings, 2),
            "export_credit_change": round(self.export_credit_change, 2),
            "monthly_savings": {k: round(v, 2) for k, v in self.monthly_savings.items()},
        }


def _build_hourly_rate_array(tariff: Tariff, year: int = 2024) -> List[float]:
    """Build 8760-element array of energy rates $/kWh for each hour of year."""
    start = datetime.datetime(year, 1, 1)
    return [tariff.energy_rate_at(start + datetime.timedelta(hours=h)) for h in range(8760)]


def _build_hourly_export_array(export_schedule: ExportSchedule) -> List[float]:
    """Build 8760-element array of export credit rates $/kWh."""
    if export_schedule is None:
        return [0.0] * 8760
    return [export_schedule.rate_at_hour(h) for h in range(8760)]


def simulate(
    load_8760: List[float],           # kW pump load for each of 8760 hours
    solar_8760: List[float],          # kW solar generation (0 if no solar)
    tariff: Tariff,
    export_schedule: Optional[ExportSchedule],
    scenario: str = "baseline",
    year: int = 2024,
    store_hourly: bool = False,
) -> SimulationResult:
    """
    Run the hourly energy balance and bill calculation for one scenario.

    Energy balance per hour:
      grid_import = max(0, load - solar)
      grid_export = max(0, solar - load)
      self_consumed = min(solar, load)
    """
    start = datetime.datetime(year, 1, 1)

    # Build rate arrays
    energy_rates = _build_hourly_rate_array(tariff, year)
    export_rates = _build_hourly_export_array(export_schedule)

    # Monthly accumulators
    monthly_import = {m: 0.0 for m in range(1, 13)}
    monthly_export = {m: 0.0 for m in range(1, 13)}
    monthly_self_consumed = {m: 0.0 for m in range(1, 13)}
    monthly_energy_cost = {m: 0.0 for m in range(1, 13)}
    monthly_export_credit = {m: 0.0 for m in range(1, 13)}
    monthly_peak_kw = {m: 0.0 for m in range(1, 13)}
    monthly_solar = {m: 0.0 for m in range(1, 13)}

    # For demand charge: track peak within TOU windows
    # For FRD: monthly overall peak
    # For TRD: monthly peak within each TOU period
    monthly_trd_peak = {m: 0.0 for m in range(1, 13)}
    monthly_summer_peak_demand = {m: 0.0 for m in range(1, 13)}

    hourly_import = []
    hourly_net = []

    for h in range(8760):
        dt = start + datetime.timedelta(hours=h)
        month = dt.month
        is_summer = month in {6, 7, 8, 9}

        load_kw = load_8760[h] if h < len(load_8760) else 0.0
        solar_kw = solar_8760[h] if h < len(solar_8760) else 0.0

        # Energy balance
        self_consumed = min(solar_kw, load_kw)
        grid_import = max(0.0, load_kw - solar_kw)
        grid_export = max(0.0, solar_kw - load_kw)

        # Costs and credits
        energy_cost = grid_import * energy_rates[h]
        export_credit = grid_export * export_rates[h]

        # Monthly accumulation
        monthly_import[month] += grid_import
        monthly_export[month] += grid_export
        monthly_self_consumed[month] += self_consumed
        monthly_energy_cost[month] += energy_cost
        monthly_export_credit[month] += export_credit
        monthly_solar[month] += solar_kw
        monthly_peak_kw[month] = max(monthly_peak_kw[month], load_kw)

        # TRD peak: track load in peak TOU windows
        trd_rate = tariff.trd_rate_at(dt)
        if trd_rate > 0:
            monthly_trd_peak[month] = max(monthly_trd_peak[month], load_kw)

        # Summer peak demand (AG-C style)
        if is_summer and tariff.summer_peak_demand_rate > 0:
            monthly_summer_peak_demand[month] = max(
                monthly_summer_peak_demand[month], load_kw
            )

        if store_hourly:
            hourly_import.append(grid_import)

    # ── Bill calculation ──────────────────────────────────────────────────
    annual_customer = tariff.customer_charge * 12
    annual_energy = sum(monthly_energy_cost.values())
    annual_export = sum(monthly_export_credit.values())

    # FRD demand charge: each month's peak × FRD rate
    annual_frd = sum(
        monthly_peak_kw[m] * tariff.facilities_demand_rate
        for m in range(1, 13)
    )

    # TRD demand charge: peak in TOU window × TRD rate (use max TRD rate)
    max_trd_rate = max((p.demand_rate_trd for p in tariff.periods), default=0.0)
    annual_trd = sum(
        monthly_trd_peak[m] * max_trd_rate
        for m in range(1, 13)
    )

    # Summer peak demand (AG-C)
    annual_summer_peak = sum(
        monthly_summer_peak_demand[m] * tariff.summer_peak_demand_rate
        for m in {6, 7, 8, 9}
    )

    annual_total = (
        annual_customer +
        annual_energy +
        annual_frd +
        annual_trd +
        annual_summer_peak -
        annual_export
    )

    # ── Monthly bill breakdown ─────────────────────────────────────────────
    monthly_bills = {}
    for m in range(1, 13):
        trd = monthly_trd_peak[m] * max_trd_rate
        summer_pk = monthly_summer_peak_demand[m] * tariff.summer_peak_demand_rate
        frd = monthly_peak_kw[m] * tariff.facilities_demand_rate
        total = (
            tariff.customer_charge +
            monthly_energy_cost[m] +
            frd + trd + summer_pk -
            monthly_export_credit[m]
        )
        monthly_bills[m] = {
            "customer_charge": round(tariff.customer_charge, 2),
            "energy_charge": round(monthly_energy_cost[m], 2),
            "demand_frd": round(frd, 2),
            "demand_trd": round(trd, 2),
            "demand_summer_peak": round(summer_pk, 2),
            "export_credit": round(-monthly_export_credit[m], 2),
            "total": round(total, 2),
        }

    return SimulationResult(
        scenario=scenario,
        total_energy_kwh=round(sum(load_8760), 1),
        total_grid_import_kwh=round(sum(monthly_import.values()), 1),
        total_solar_self_consumed_kwh=round(sum(monthly_self_consumed.values()), 1),
        total_solar_exported_kwh=round(sum(monthly_export.values()), 1),
        peak_kw_annual=round(max(monthly_peak_kw.values()), 2),
        annual_customer_charge=round(annual_customer, 2),
        annual_energy_charge=round(annual_energy, 2),
        annual_demand_charge_frd=round(annual_frd, 2),
        annual_demand_charge_trd=round(annual_trd, 2),
        annual_demand_charge_summer_peak=round(annual_summer_peak, 2),
        annual_export_credit=round(annual_export, 2),
        annual_total_bill=round(annual_total, 2),
        monthly_bills=monthly_bills,
        monthly_kwh={m: round(monthly_import[m], 1) for m in range(1, 13)},
        monthly_peak_kw={m: round(monthly_peak_kw[m], 2) for m in range(1, 13)},
        monthly_solar_kwh={m: round(monthly_solar[m], 1) for m in range(1, 13)},
        hourly_load=load_8760 if store_hourly else None,
        hourly_solar=solar_8760 if store_hourly else None,
        hourly_grid_import=hourly_import if store_hourly else None,
    )
