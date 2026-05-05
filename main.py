import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import traceback

from simulator.runner import FarmConfig, run_simulation
from tariffs import REGISTRY
from load_synth.crops import CROPS, CROP_GROUPS
from load_synth.irrigation import IRRIGATION_SYSTEMS
from load_synth.engine import CLIMATE_REGIONS

app = FastAPI(title="SunBreak Dashboard")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class SimRequest(BaseModel):
    farm_name: str = "My Farm"
    utility: str = "PG&E"
    tariff_key: str = "PG&E:AG-B"
    climate_region: str = "central_valley"
    lat: float = 36.75
    lon: float = -119.77
    crop_name: str = "almond"
    irrigation_type: str = "drip"
    area_acres: float = 200.0
    pump_kw: float = 75.0
    total_dynamic_head_ft: Optional[float] = None
    has_solar: bool = False
    solar_kw_dc: float = 0.0
    nem_program: str = "NBT"
    nem_vintage_year: int = 2025

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/meta")
async def get_meta():
    return {
        "tariffs": list(REGISTRY.keys()),
        "crops": {k: {"display_name": v.display_name, "crop_type": v.crop_type, "irrigation_systems": v.irrigation_systems} for k, v in CROPS.items()},
        "crop_groups": CROP_GROUPS,
        "irrigation_systems": {k: {"display_name": v.display_name, "efficiency": v.efficiency, "scheduling_flexibility": v.scheduling_flexibility} for k, v in IRRIGATION_SYSTEMS.items()},
        "climate_regions": {k: v["name"] for k, v in CLIMATE_REGIONS.items()},
        "utilities": {
            "PG&E": [k for k in REGISTRY if k.startswith("PG&E")],
            "SCE": [k for k in REGISTRY if k.startswith("SCE")],
            "SDG&E": [k for k in REGISTRY if k.startswith("SDG&E")],
        }
    }

@app.post("/api/simulate")
async def simulate_endpoint(req: SimRequest):
    try:
        config = FarmConfig(
            farm_name=req.farm_name, utility=req.utility, tariff_key=req.tariff_key,
            climate_region=req.climate_region, lat=req.lat, lon=req.lon,
            crop_name=req.crop_name, irrigation_type=req.irrigation_type,
            area_acres=req.area_acres, pump_kw=req.pump_kw,
            total_dynamic_head_ft=req.total_dynamic_head_ft,
            has_solar=req.has_solar, solar_kw_dc=req.solar_kw_dc,
            nem_program=req.nem_program, nem_vintage_year=req.nem_vintage_year,
        )
        report = run_simulation(config)
        return JSONResponse(content={"status": "ok", "data": report.summary()})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e), "trace": traceback.format_exc()})

@app.get("/api/presets")
async def get_presets():
    return [
        {"label": "PG&E — Almond Ranch (350 ac)", "utility":"PG&E","tariff_key":"PG&E:AG-B","climate_region":"central_valley","lat":36.75,"lon":-119.77,"crop_name":"almond","irrigation_type":"drip","area_acres":350,"pump_kw":300,"has_solar":True,"solar_kw_dc":200,"nem_program":"NBT"},
        {"label": "PG&E — Alfalfa Center Pivot (500 ac)", "utility":"PG&E","tariff_key":"PG&E:AG-B","climate_region":"sacramento_valley","lat":38.58,"lon":-121.49,"crop_name":"alfalfa","irrigation_type":"center_pivot","area_acres":500,"pump_kw":200,"has_solar":False,"solar_kw_dc":0,"nem_program":"NBT"},
        {"label": "PG&E — Large Walnut Ranch AG-C (700 ac)", "utility":"PG&E","tariff_key":"PG&E:AG-C","climate_region":"sacramento_valley","lat":38.20,"lon":-121.80,"crop_name":"walnut","irrigation_type":"drip","area_acres":700,"pump_kw":500,"has_solar":True,"solar_kw_dc":400,"nem_program":"NBT"},
        {"label": "SCE — San Joaquin Citrus (180 ac)", "utility":"SCE","tariff_key":"SCE:TOU-PA-2-D","climate_region":"central_valley","lat":36.60,"lon":-119.00,"crop_name":"citrus","irrigation_type":"drip","area_acres":180,"pump_kw":125,"has_solar":True,"solar_kw_dc":100,"nem_program":"NBT"},
        {"label": "SCE — Coachella Table Grape (120 ac)", "utility":"SCE","tariff_key":"SCE:TOU-PA-2-D-5TO8","climate_region":"coachella_imperial","lat":33.72,"lon":-116.22,"crop_name":"table_grape","irrigation_type":"drip","area_acres":120,"pump_kw":100,"has_solar":True,"solar_kw_dc":80,"nem_program":"NBT"},
        {"label": "SCE — Imperial Cotton Flood (600 ac)", "utility":"SCE","tariff_key":"SCE:TOU-PA-2-E","climate_region":"coachella_imperial","lat":32.79,"lon":-115.57,"crop_name":"cotton","irrigation_type":"flood","area_acres":600,"pump_kw":400,"has_solar":False,"solar_kw_dc":0,"nem_program":"NBT"},
        {"label": "SDG&E — San Diego Avocado (60 ac)", "utility":"SDG&E","tariff_key":"SDG&E:TOU-PA","climate_region":"southern_california","lat":33.20,"lon":-117.10,"crop_name":"avocado","irrigation_type":"drip","area_acres":60,"pump_kw":37,"has_solar":True,"solar_kw_dc":30,"nem_program":"NBT"},
        {"label": "SDG&E — Salinas Lettuce Sprinkler (150 ac)", "utility":"SDG&E","tariff_key":"SDG&E:AL-TOU","climate_region":"coastal_central","lat":36.68,"lon":-121.64,"crop_name":"lettuce","irrigation_type":"sprinkler","area_acres":150,"pump_kw":50,"has_solar":True,"solar_kw_dc":40,"nem_program":"NBT"},
        {"label": "SDG&E — Ventura Strawberry (90 ac)", "utility":"SDG&E","tariff_key":"SDG&E:AL-TOU","climate_region":"coastal_central","lat":34.28,"lon":-119.29,"crop_name":"strawberry","irrigation_type":"drip","area_acres":90,"pump_kw":37,"has_solar":True,"solar_kw_dc":30,"nem_program":"NBT"},
    ]
