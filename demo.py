#!/usr/bin/env python3
"""
SunBreak Savings Simulation — Demo Runner

12 farm scenarios across PG&E, SCE, and SDG&E covering all major CA
crop types and all four irrigation system archetypes.

Pump sizes are hydraulically matched to acreage for realistic runtimes.
"""

import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simulator.runner import run_simulation, FarmConfig

SCENARIOS = [
    # ── PG&E Territory ──────────────────────────────────────────────────
    FarmConfig(
        farm_name="Central Valley Almond Ranch",
        utility="PG&E", tariff_key="PG&E:AG-B",
        climate_region="central_valley", lat=36.75, lon=-119.77,
        crop_name="almond", irrigation_type="drip",
        area_acres=350, pump_kw=300, total_dynamic_head_ft=180,
        has_solar=True, solar_kw_dc=200,
        nem_program="NBT", nem_vintage_year=2025,
    ),
    FarmConfig(
        farm_name="Sacramento Valley Alfalfa (Center Pivot)",
        utility="PG&E", tariff_key="PG&E:AG-B",
        climate_region="sacramento_valley", lat=38.58, lon=-121.49,
        crop_name="alfalfa", irrigation_type="center_pivot",
        area_acres=500, pump_kw=200, total_dynamic_head_ft=80,
        has_solar=False, nem_program="NBT",
    ),
    FarmConfig(
        farm_name="Small Pistachio Farm (NEM2 Grandfathered)",
        utility="PG&E", tariff_key="PG&E:AG-A2",
        climate_region="central_valley", lat=36.31, lon=-119.45,
        crop_name="pistachio", irrigation_type="drip",
        area_acres=80, pump_kw=100, total_dynamic_head_ft=200,
        has_solar=True, solar_kw_dc=75,
        nem_program="NEM2",
    ),
    FarmConfig(
        farm_name="Large Walnut Ranch (AG-C Large Demand)",
        utility="PG&E", tariff_key="PG&E:AG-C",
        climate_region="sacramento_valley", lat=38.20, lon=-121.80,
        crop_name="walnut", irrigation_type="drip",
        area_acres=700, pump_kw=500, total_dynamic_head_ft=170,
        has_solar=True, solar_kw_dc=400,
        nem_program="NBT", nem_vintage_year=2025,
    ),
    # ── SCE Territory ────────────────────────────────────────────────────
    FarmConfig(
        farm_name="San Joaquin Citrus Ranch",
        utility="SCE", tariff_key="SCE:TOU-PA-2-D",
        climate_region="central_valley", lat=36.60, lon=-119.00,
        crop_name="citrus", irrigation_type="drip",
        area_acres=180, pump_kw=125, total_dynamic_head_ft=150,
        has_solar=True, solar_kw_dc=100,
        nem_program="NBT", nem_vintage_year=2025,
    ),
    FarmConfig(
        farm_name="Coachella Table Grape Vineyard",
        utility="SCE", tariff_key="SCE:TOU-PA-2-D-5TO8",
        climate_region="coachella_imperial", lat=33.72, lon=-116.22,
        crop_name="table_grape", irrigation_type="drip",
        area_acres=120, pump_kw=100, total_dynamic_head_ft=160,
        has_solar=True, solar_kw_dc=80,
        nem_program="NBT", nem_vintage_year=2025,
    ),
    FarmConfig(
        farm_name="Imperial Valley Cotton (Flood — Low Flexibility)",
        utility="SCE", tariff_key="SCE:TOU-PA-2-E",
        climate_region="coachella_imperial", lat=32.79, lon=-115.57,
        crop_name="cotton", irrigation_type="flood",
        area_acres=600, pump_kw=400, total_dynamic_head_ft=60,
        has_solar=False, nem_program="NBT",
    ),
    FarmConfig(
        farm_name="Processing Tomato — Sprinkler (Large SCE)",
        utility="SCE", tariff_key="SCE:TOU-PA-3-D",
        climate_region="central_valley", lat=36.80, lon=-119.90,
        crop_name="processing_tomato", irrigation_type="sprinkler",
        area_acres=400, pump_kw=400, total_dynamic_head_ft=130,
        has_solar=True, solar_kw_dc=300,
        nem_program="NBT", nem_vintage_year=2025,
    ),
    # ── SDG&E Territory ──────────────────────────────────────────────────
    FarmConfig(
        farm_name="San Diego Avocado Ranch",
        utility="SDG&E", tariff_key="SDG&E:TOU-PA",
        climate_region="southern_california", lat=33.20, lon=-117.10,
        crop_name="avocado", irrigation_type="drip",
        area_acres=60, pump_kw=37, total_dynamic_head_ft=120,
        has_solar=True, solar_kw_dc=30,
        nem_program="NBT", nem_vintage_year=2025,
    ),
    FarmConfig(
        farm_name="Salinas Lettuce Farm (Sprinkler)",
        utility="SDG&E", tariff_key="SDG&E:AL-TOU",
        climate_region="coastal_central", lat=36.68, lon=-121.64,
        crop_name="lettuce", irrigation_type="sprinkler",
        area_acres=150, pump_kw=50, total_dynamic_head_ft=100,
        has_solar=True, solar_kw_dc=40,
        nem_program="NBT", nem_vintage_year=2025,
    ),
    FarmConfig(
        farm_name="Ventura Strawberry Farm",
        utility="SDG&E", tariff_key="SDG&E:AL-TOU",
        climate_region="coastal_central", lat=34.28, lon=-119.29,
        crop_name="strawberry", irrigation_type="drip",
        area_acres=90, pump_kw=37, total_dynamic_head_ft=90,
        has_solar=True, solar_kw_dc=30,
        nem_program="NBT", nem_vintage_year=2025,
    ),
    FarmConfig(
        farm_name="San Diego Wine Vineyard (Large)",
        utility="SDG&E", tariff_key="SDG&E:ALTOU-P",
        climate_region="southern_california", lat=33.05, lon=-116.85,
        crop_name="wine_grape", irrigation_type="drip",
        area_acres=250, pump_kw=150, total_dynamic_head_ft=140,
        has_solar=True, solar_kw_dc=120,
        nem_program="NBT", nem_vintage_year=2025,
    ),
]

QUICK_SCENARIOS = [0, 4, 8]  # PG&E almond, SCE citrus, SDG&E avocado

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


def print_banner():
    print("=" * 72)
    print("  SUNBREAK AGRICULTURAL SAVINGS SIMULATION  v1.0")
    print("  Utilities : PG&E  |  SCE  |  SDG&E")
    print("  Crops     : Almonds, Pistachios, Walnuts, Citrus, Avocados,")
    print("              Table Grapes, Wine Grapes, Alfalfa, Cotton,")
    print("              Processing Tomatoes, Lettuce, Strawberries")
    print("  Irrigation: Drip | Center Pivot | Flood/Furrow | Sprinkler")
    print("=" * 72)


def print_result(idx, report):
    s = report.summary()
    print(f"\n{'═'*72}")
    print(f"  [{idx+1}] {s['farm']}")
    print(f"  {s['utility']}  |  {s['tariff']}  |  {s['crop'].replace('_',' ').title()}"
          f"  |  {s['irrigation'].replace('_',' ').title()}")
    print(f"  {s['area_acres']} acres  |  {s['pump_kw']} kW pump  |  "
          f"{s['solar_kw_dc']} kW DC solar")
    print(f"{'═'*72}")
    print(f"  {'Baseline Annual Bill:':40s} ${s['baseline_annual_bill']:>12,.2f}")
    print(f"  {'Optimized Annual Bill (SunBreak):':40s} ${s['optimized_annual_bill']:>12,.2f}")
    marker = "✓ SAVINGS" if s['annual_savings'] > 0 else "✗"
    print(f"  {'Annual Savings:':40s} ${s['annual_savings']:>12,.2f}  {s['savings_pct']:.1f}%  {marker}")
    print(f"  {'─'*68}")
    print(f"  Breakdown:")
    print(f"    TOU Energy Charge Savings:           ${s['energy_charge_savings']:>10,.2f}")
    print(f"    Demand Charge Savings:               ${s['demand_charge_savings']:>10,.2f}")
    print(f"    Solar Self-Consumption Savings:      ${s['solar_self_consumption_savings']:>10,.2f}")
    print(f"    Export Credit Change:                ${s['export_credit_change']:>+10,.2f}")
    print(f"  {'─'*68}")
    print(f"  Monthly Savings:")
    monthly = s["monthly_savings"]
    max_save = max(abs(v) for v in monthly.values()) if monthly else 1
    for i, name in enumerate(MONTHS):
        m = i + 1
        val = monthly.get(m, 0)
        bar_len = int(abs(val) / max_save * 28) if max_save > 0 else 0
        bar = ("█" * bar_len) if val > 0 else ("░" * bar_len)
        sign = "+" if val >= 0 else "-"
        print(f"    {name}: {sign}${abs(val):>7,.0f}  {bar}")


def run_all(indices=None):
    print_banner()
    to_run = [SCENARIOS[i] for i in indices] if indices else SCENARIOS
    results = []
    for seq, config in enumerate(to_run):
        real_idx = indices[seq] if indices else seq
        print(f"\n[{real_idx+1}/{len(SCENARIOS)}] {config.farm_name}")
        try:
            report = run_simulation(config)
            results.append((real_idx, report))
            print_result(real_idx, report)
        except Exception as e:
            import traceback
            print(f"  ERROR: {e}")
            traceback.print_exc()

    if results:
        print(f"\n{'='*72}")
        print(f"  SUMMARY TABLE")
        print(f"{'='*72}")
        print(f"  {'Farm':<38} {'Util':>6} {'Crop':>18} {'Baseline':>10} {'Savings':>10} {'%':>6}")
        print(f"  {'─'*72}")
        for idx, r in results:
            s = r.summary()
            farm = s['farm'][:38]
            crop = s['crop'].replace('_',' ').title()[:18]
            util = s['utility']
            print(f"  {farm:<38} {util:>6} {crop:>18} "
                  f"${s['baseline_annual_bill']:>9,.0f} "
                  f"${s['annual_savings']:>9,.0f} "
                  f"{s['savings_pct']:>5.1f}%")
        total_savings = sum(r.annual_bill_savings for _, r in results)
        total_baseline = sum(r.baseline.annual_total_bill for _, r in results)
        avg_pct = total_savings / total_baseline * 100 if total_baseline else 0
        print(f"  {'─'*72}")
        print(f"  {'TOTAL / AVERAGE':<38} {'':>6} {'':>18} "
              f"${total_baseline:>9,.0f} ${total_savings:>9,.0f} {avg_pct:>5.1f}%")
        print()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Run 3 representative scenarios")
    parser.add_argument("--scenario", type=int, metavar="N", help="Run single scenario (1-based)")
    parser.add_argument("--json", action="store_true", help="Also output JSON")
    args = parser.parse_args()

    if args.scenario:
        results = run_all([args.scenario - 1])
    elif args.quick:
        results = run_all(QUICK_SCENARIOS)
    else:
        results = run_all()

    if args.json and results:
        print(json.dumps([r.summary() for _, r in results], indent=2))
