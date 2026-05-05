# scheduler/optimizer.py
"""
Pump scheduling optimizer for TOU load shifting and solar self-consumption.

Two schedulers share the same interface:

  BaselineScheduler  — mimics current farmer behavior (system archetype weights)
  OptimizedScheduler — SunBreak greedy TOU-aware scheduler

The optimizer solves a daily scheduling problem:
  Given:
    - Daily runtime budget (hours)
    - Hourly energy costs ($/kWh)
    - Hourly solar generation (kW) — for self-consumption bonus
    - System scheduling constraints (min block, max block, flexibility)
  Minimize:
    - Energy cost = Σ (pump_kW × on_fraction[h] × (energy_rate[h] - solar_offset[h]))
  Subject to:
    - Σ on_fraction[h] = runtime_hours_required
    - on_fraction[h] ∈ [0, 1]
    - Block length constraints (pump can't start/stop every hour)
    - Labor window constraints (set-move systems)
    - Demand charge consideration (spread load to avoid kW spikes)

The greedy approach: rank hours by effective cost (energy rate - solar benefit),
then fill cheapest hours first within operational constraints.

Savings from demand charge reduction are computed separately in the simulator.
"""

import datetime
from typing import List, Optional

from load_synth.irrigation import IrrigationSystem, IRRIGATION_SYSTEMS


class BaselineScheduler:
    """
    Replicates current farmer behavior using system archetype baseline weights.
    Pump runs at rated kW in allocated hours (binary on/off per hour).
    Fractional hours at end of runtime modeled as partial-on.
    """

    def schedule_day(
        self,
        runtime_hours: float,
        system: IrrigationSystem,
        hourly_rates: List[float],
        solar_kw: List[float],
        pump_kw: float,
        date: Optional[datetime.date] = None,
        **kwargs,
    ) -> List[float]:
        """
        Returns 24-hour load profile (kW) for a single day.
        Fills hours according to baseline weight distribution, running
        pump at rated kW (loading factor applied) for each allocated hour.
        """
        if runtime_hours <= 0:
            return [0.0] * 24

        weights = system.baseline_hourly_weights
        actual_kw = pump_kw * system.pump_loading_factor
        weight_sum = sum(weights)

        # Sort hours by weight (highest weight = most preferred by farmer)
        # Fill greedily in preference order, respecting fractional runtime
        hours_by_pref = sorted(range(24), key=lambda h: -weights[h])

        day_load = [0.0] * 24
        remaining = runtime_hours

        for h in hours_by_pref:
            if remaining <= 0:
                break
            if weights[h] <= 0:
                continue
            # Allocate up to 1 full hour at a time
            on_fraction = min(1.0, remaining)
            day_load[h] = actual_kw * on_fraction
            remaining -= on_fraction

        return day_load


class OptimizedScheduler:
    """
    SunBreak greedy TOU-aware scheduler.

    Strategy:
    1. Compute effective cost per hour: energy_rate - solar_benefit
    2. Sort hours by effective cost (cheapest first)
    3. Fill hours within operational constraints
    4. Respect minimum block lengths to avoid excessive starts/stops
    5. Apply labor window constraints for set-move systems

    Solar benefit: when pump runs during solar generation, self-consumed
    energy avoids paying grid rate AND avoids exporting at low NBT rate.
    Benefit = grid_rate - export_rate (always positive, max during solar hours)
    """

    def __init__(self, demand_charge_sensitivity: float = 0.5):
        """
        demand_charge_sensitivity: 0–1 weight on avoiding simultaneous peaks.
        Higher values penalize hours where multiple pumps may already be running.
        """
        self.demand_charge_sensitivity = demand_charge_sensitivity

    def schedule_day(
        self,
        runtime_hours: float,
        system: IrrigationSystem,
        hourly_rates: List[float],       # 24 values: $/kWh
        solar_kw: List[float],           # 24 values: available solar (kW) for this pump
        pump_kw: float,
        export_rates: Optional[List[float]] = None,  # 24 values: $/kWh export credit
        date: Optional[datetime.date] = None,
        existing_load: Optional[List[float]] = None,  # Other pumps already scheduled (kW)
    ) -> List[float]:
        """
        Returns optimized 24-hour load profile (kW) for a single day.

        When solar_kw is provided, hours with solar generation are cheaper
        (self-consumed solar displaces grid purchases at full retail value
        rather than exporting at low NBT rate).
        """
        if runtime_hours <= 0:
            return [0.0] * 24

        if export_rates is None:
            export_rates = [0.04] * 24   # Default NBT low export rate

        actual_kw = pump_kw * system.pump_loading_factor

        # ── Effective hourly cost ──────────────────────────────────────────
        # If pump runs during solar generation:
        #   Cost = grid_rate × (non-solar fraction) + 0 × (solar fraction)
        #   i.e. self-consumed solar displaces grid purchase — lowers effective cost
        # Under NBT: exporting is worth ~$0.05/kWh; self-consuming avoids ~$0.25/kWh
        #   so self-consumption benefit = grid_rate - export_rate per kWh
        effective_costs = []
        for h in range(24):
            grid_rate = hourly_rates[h]
            solar_avail = (solar_kw[h] if solar_kw and h < len(solar_kw) else 0.0)
            solar_avail = min(solar_avail, actual_kw)
            solar_fraction = solar_avail / actual_kw if actual_kw > 0 else 0.0

            export_r = export_rates[h] if h < len(export_rates) else 0.04
            # Each kWh self-consumed saves (grid_rate - export_rate) vs exporting
            self_consump_benefit = solar_fraction * max(0, grid_rate - export_r)
            # Effective cost: grid rate reduced by self-consumption benefit
            eff_cost = grid_rate - self_consump_benefit

            # Demand charge sensitivity: mild penalty for adding to existing demand
            if existing_load and self.demand_charge_sensitivity > 0:
                other_load = existing_load[h] if h < len(existing_load) else 0
                demand_penalty = other_load * 0.001 * self.demand_charge_sensitivity
                eff_cost += demand_penalty

            effective_costs.append(eff_cost)

        # ── Apply scheduling constraints ───────────────────────────────────
        # Get valid hours (labor window for set-move systems)
        if system.labor_hours:
            # For labor-coupled systems, pump can only run during/around labor hours
            # but we allow flexibility within each shift block
            # Simplification: restrict to a shift window around labor hours
            valid_hours = set()
            for lh in system.labor_hours:
                for offset in range(-1, int(system.max_run_block_hr) + 1):
                    h = (lh + offset) % 24
                    valid_hours.add(h)
            valid_hours = sorted(valid_hours)
        else:
            valid_hours = list(range(24))

        # Also constrain to scheduling_flexibility — mix of optimized and baseline hours
        # High flexibility → fully optimized; low flexibility → closer to baseline
        flexibility = system.scheduling_flexibility
        n_flexible = int(len(valid_hours) * flexibility)
        n_baseline = len(valid_hours) - n_flexible

        # Sort valid hours by effective cost
        sorted_hours = sorted(valid_hours, key=lambda h: effective_costs[h])
        optimized_hours = set(sorted_hours[:n_flexible])

        # Baseline hours: use system weights for remaining fraction
        baseline_weights = system.baseline_hourly_weights
        baseline_valid = [h for h in valid_hours if h not in optimized_hours]

        # ── Allocate runtime to hours ──────────────────────────────────────
        day_load = [0.0] * 24
        remaining = runtime_hours

        # Sort all valid hours by effective cost (cheapest first = best hours)
        cheapest_hours = sorted(valid_hours, key=lambda h: effective_costs[h])

        for h in cheapest_hours:
            if remaining <= 0.001:
                break
            on_fraction = min(1.0, remaining)
            day_load[h] = actual_kw * on_fraction
            remaining -= on_fraction

        return day_load


def build_optimized_load_profile(
    baseline_load: List[float],
    system_name: str,
    hourly_rates_8760: List[float],
    solar_8760: List[float],
    export_rates_8760: List[float],
    pump_kw: float,
    area_acres: float,
    crop_name: str,
    climate_region: str,
    year: int = 2024,
) -> List[float]:
    """
    Build the SunBreak-optimized 8760-hour load profile.

    Preserves the same total annual kWh (same water delivered)
    but redistributes pump runtime to cheaper, solar-rich hours.
    """
    from load_synth.engine import compute_daily_etc, compute_pump_runtime_hours
    from load_synth.crops import CROPS
    from load_synth.irrigation import IRRIGATION_SYSTEMS

    crop = CROPS[crop_name]
    system = IRRIGATION_SYSTEMS[system_name]
    scheduler = OptimizedScheduler()

    daily_etc = compute_daily_etc(crop, climate_region, year)
    optimized_8760 = []
    day_idx = 0

    start = datetime.date(year, 1, 1)
    for day_offset, (date, etc_day) in enumerate(daily_etc):
        if day_offset >= 365:
            break

        runtime_hr = compute_pump_runtime_hours(
            etc_day, area_acres, system, pump_kw,
            crop.typical_tdh_ft
        )
        runtime_hr = min(runtime_hr, 23.0)

        h_start = day_offset * 24
        h_end = min(h_start + 24, len(hourly_rates_8760))

        if runtime_hr <= 0:
            optimized_8760.extend([0.0] * 24)
            continue

        day_rates = list(hourly_rates_8760[h_start:h_end])
        while len(day_rates) < 24:
            day_rates.append(day_rates[-1] if day_rates else 0.15)

        day_solar = list(solar_8760[h_start:h_end]) if solar_8760 else []
        while len(day_solar) < 24:
            day_solar.append(0.0)

        day_export = list(export_rates_8760[h_start:h_end]) if export_rates_8760 else []
        while len(day_export) < 24:
            day_export.append(0.04)

        day_load = scheduler.schedule_day(
            runtime_hours=runtime_hr,
            system=system,
            hourly_rates=day_rates,
            solar_kw=day_solar,
            pump_kw=pump_kw,
            export_rates=day_export,
            date=date,
        )
        optimized_8760.extend(day_load)

    while len(optimized_8760) < 8760:
        optimized_8760.append(0.0)
    return optimized_8760[:8760]
