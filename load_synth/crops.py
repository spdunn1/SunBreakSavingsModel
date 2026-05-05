# load_synth/crops.py
"""
Crop coefficients (Kc) and irrigation seasonality for major California crops.

Source: UC ANR Leaflets 21427 (agronomic/grass/vegetable) and 21428 (trees/vines)
        CIMIS crop coefficient tables
        UC Davis LAWR irrigation guidelines

Kc values are monthly averages by growth stage.
Stage: initial → development → mid-season → late → harvest

Format: monthly Kc values (Jan=index 0) representing a mature, full-season crop.
Crops with multiple harvests or perennial patterns use annualized seasonal shape.

For a multi-year perennial, these represent the pattern during an average year.
For annuals, values are 0.0 outside the growing season.

Energy intensity of irrigation:
  kWh/acre-inch = (TDH_ft × 0.746) / (3960 × η_pump × η_motor)
  Typical TDH: 100–300 ft for groundwater wells, 20–80 ft for surface/canal
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class CropProfile:
    name: str
    display_name: str
    crop_type: str          # "tree", "vine", "row", "field", "vegetable"
    kc_monthly: List[float]  # Jan–Dec, 12 values
    peak_season_months: List[int]  # 1-based months with highest water demand
    irrigation_systems: List[str]  # Compatible system types
    typical_tdh_ft: float   # Typical total dynamic head for this crop region
    notes: str = ""

    @property
    def kc(self) -> Dict[int, float]:
        """Return dict mapping month (1-12) to Kc."""
        return {i + 1: v for i, v in enumerate(self.kc_monthly)}

    def kc_at_month(self, month: int) -> float:
        return self.kc_monthly[month - 1]


# ─────────────────────────────────────────────────────────────────────────────
# TREE CROPS
# ─────────────────────────────────────────────────────────────────────────────

ALMOND = CropProfile(
    name="almond",
    display_name="Almonds",
    crop_type="tree",
    kc_monthly=[
        0.40,  # Jan (dormant)
        0.55,  # Feb (bloom)
        0.80,  # Mar (hull split)
        1.00,  # Apr
        1.15,  # May (peak ET)
        1.15,  # Jun (peak ET)
        1.10,  # Jul
        0.95,  # Aug (harvest)
        0.60,  # Sep (post-harvest)
        0.45,  # Oct
        0.35,  # Nov
        0.35,  # Dec
    ],
    peak_season_months=[5, 6, 7],
    irrigation_systems=["drip", "microsprinkler"],
    typical_tdh_ft=180,
    notes="Central Valley primary crop. Drip dominant post-2015. Peak ET May–Jul."
)

PISTACHIO = CropProfile(
    name="pistachio",
    display_name="Pistachios",
    crop_type="tree",
    kc_monthly=[
        0.00,  # Jan (fully dormant)
        0.00,  # Feb
        0.35,  # Mar (bud break)
        0.80,  # Apr
        1.10,  # May
        1.20,  # Jun (peak)
        1.20,  # Jul (peak)
        1.05,  # Aug (hull split/harvest)
        0.70,  # Sep
        0.45,  # Oct
        0.10,  # Nov
        0.00,  # Dec
    ],
    peak_season_months=[6, 7, 8],
    irrigation_systems=["drip", "microsprinkler"],
    typical_tdh_ft=200,
    notes="Alternate-bearing variety. Longer dormancy than almonds."
)

WALNUT = CropProfile(
    name="walnut",
    display_name="Walnuts",
    crop_type="tree",
    kc_monthly=[
        0.35,  # Jan
        0.45,  # Feb
        0.70,  # Mar
        0.95,  # Apr
        1.10,  # May
        1.15,  # Jun
        1.15,  # Jul
        1.05,  # Aug (harvest Sep–Oct)
        0.90,  # Sep
        0.60,  # Oct
        0.40,  # Nov
        0.35,  # Dec
    ],
    peak_season_months=[6, 7, 8],
    irrigation_systems=["drip", "microsprinkler", "sprinkler"],
    typical_tdh_ft=170,
    notes="Sacramento Valley primary region."
)

CITRUS = CropProfile(
    name="citrus",
    display_name="Citrus (Navel/Valencia)",
    crop_type="tree",
    kc_monthly=[
        0.70,  # Jan (evergreen, no dormancy)
        0.70,  # Feb
        0.75,  # Mar (bloom)
        0.80,  # Apr
        0.85,  # May
        0.90,  # Jun
        0.95,  # Jul (peak)
        0.95,  # Aug
        0.90,  # Sep
        0.85,  # Oct
        0.80,  # Nov
        0.75,  # Dec
    ],
    peak_season_months=[7, 8, 9],
    irrigation_systems=["drip", "microsprinkler"],
    typical_tdh_ft=150,
    notes="Evergreen — year-round irrigation required. Tulare/Ventura counties."
)

AVOCADO = CropProfile(
    name="avocado",
    display_name="Avocados",
    crop_type="tree",
    kc_monthly=[
        0.75,  # Jan
        0.75,  # Feb (bloom)
        0.80,  # Mar
        0.85,  # Apr
        0.90,  # May
        1.00,  # Jun (fruit set)
        1.05,  # Jul (peak)
        1.05,  # Aug
        0.95,  # Sep
        0.85,  # Oct
        0.80,  # Nov
        0.75,  # Dec
    ],
    peak_season_months=[7, 8, 9],
    irrigation_systems=["drip", "microsprinkler"],
    typical_tdh_ft=120,   # SDG&E territory, often hillside — head varies
    notes="SDG&E territory primary. Shallow rooted, stress-sensitive. "
          "High-frequency micro-irrigation standard."
)

# ─────────────────────────────────────────────────────────────────────────────
# VINE CROPS
# ─────────────────────────────────────────────────────────────────────────────

WINE_GRAPE = CropProfile(
    name="wine_grape",
    display_name="Wine Grapes",
    crop_type="vine",
    kc_monthly=[
        0.15,  # Jan (dormant)
        0.15,  # Feb
        0.30,  # Mar (bud break)
        0.55,  # Apr
        0.75,  # May (shoot growth)
        0.85,  # Jun (bloom/set)
        0.90,  # Jul (veraison)
        0.85,  # Aug (ripening)
        0.65,  # Sep (harvest)
        0.45,  # Oct (post-harvest)
        0.20,  # Nov
        0.10,  # Dec
    ],
    peak_season_months=[7, 8],
    irrigation_systems=["drip"],
    typical_tdh_ft=140,
    notes="Regulated deficit irrigation common post-veraison. "
          "Coast ranges and Central Valley foothills."
)

TABLE_GRAPE = CropProfile(
    name="table_grape",
    display_name="Table Grapes",
    crop_type="vine",
    kc_monthly=[
        0.10,  # Jan
        0.10,  # Feb
        0.30,  # Mar
        0.65,  # Apr
        0.90,  # May
        1.05,  # Jun (peak)
        1.05,  # Jul
        0.95,  # Aug (harvest)
        0.70,  # Sep
        0.40,  # Oct
        0.15,  # Nov
        0.10,  # Dec
    ],
    peak_season_months=[6, 7],
    irrigation_systems=["drip"],
    typical_tdh_ft=160,
    notes="Coachella/San Joaquin Valley. Higher Kc than wine grape."
)

# ─────────────────────────────────────────────────────────────────────────────
# ROW / FIELD CROPS
# ─────────────────────────────────────────────────────────────────────────────

ALFALFA = CropProfile(
    name="alfalfa",
    display_name="Alfalfa",
    crop_type="field",
    kc_monthly=[
        0.85,  # Jan (perennial, multiple cuttings/year)
        0.90,  # Feb
        1.00,  # Mar
        1.10,  # Apr
        1.15,  # May (peak)
        1.15,  # Jun (peak, ~5–6 cuttings/season)
        1.10,  # Jul
        1.10,  # Aug
        1.05,  # Sep
        0.95,  # Oct
        0.90,  # Nov
        0.85,  # Dec
    ],
    peak_season_months=[5, 6, 7, 8],
    irrigation_systems=["flood", "sprinkler", "center_pivot"],
    typical_tdh_ft=80,  # Often canal-fed, lower head
    notes="Highest water use of any CA crop. 6+ acre-ft/year typical. "
          "Imperial/San Joaquin valleys. Often flood-irrigated."
)

PROCESSING_TOMATO = CropProfile(
    name="processing_tomato",
    display_name="Processing Tomatoes",
    crop_type="row",
    kc_monthly=[
        0.00,  # Jan (not planted)
        0.00,  # Feb
        0.00,  # Mar
        0.35,  # Apr (transplant)
        0.70,  # May (vegetative)
        1.05,  # Jun (flower/fruit set)
        1.20,  # Jul (peak ET)
        1.10,  # Aug (maturation)
        0.75,  # Sep (harvest, dry-down)
        0.00,  # Oct
        0.00,  # Nov
        0.00,  # Dec
    ],
    peak_season_months=[7, 8],
    irrigation_systems=["drip", "sprinkler", "furrow"],
    typical_tdh_ft=130,
    notes="Sacramento Valley primary. Drip replacing furrow for water efficiency. "
          "Short season Apr–Sep."
)

COTTON = CropProfile(
    name="cotton",
    display_name="Cotton",
    crop_type="field",
    kc_monthly=[
        0.00,  # Jan
        0.00,  # Feb
        0.00,  # Mar
        0.40,  # Apr (emergence)
        0.75,  # May (vegetative)
        1.05,  # Jun (squaring)
        1.20,  # Jul (peak, boll development)
        1.15,  # Aug
        0.85,  # Sep (boll opening)
        0.40,  # Oct (defoliation/harvest)
        0.00,  # Nov
        0.00,  # Dec
    ],
    peak_season_months=[7, 8],
    irrigation_systems=["furrow", "drip", "sprinkler"],
    typical_tdh_ft=100,
    notes="San Joaquin Valley. High summer demand coincides with peak TOU rates."
)

# ─────────────────────────────────────────────────────────────────────────────
# VEGETABLE CROPS
# ─────────────────────────────────────────────────────────────────────────────

LETTUCE = CropProfile(
    name="lettuce",
    display_name="Lettuce (Head/Leaf)",
    crop_type="vegetable",
    kc_monthly=[
        0.70,  # Jan (winter crop, Salinas/desert)
        0.90,  # Feb
        1.00,  # Mar (peak spring crop)
        0.90,  # Apr (harvest)
        0.50,  # May (replant, cool coast only)
        0.00,  # Jun (too hot inland)
        0.00,  # Jul
        0.35,  # Aug (fall crop starting)
        0.80,  # Sep
        1.00,  # Oct (fall peak)
        0.90,  # Nov
        0.75,  # Dec
    ],
    peak_season_months=[3, 10, 11],
    irrigation_systems=["drip", "sprinkler"],
    typical_tdh_ft=100,
    notes="Salinas Valley year-round production. Multiple cycles per year. "
          "Short-season crop (60–80 days). Very high water efficiency needed."
)

STRAWBERRY = CropProfile(
    name="strawberry",
    display_name="Strawberries",
    crop_type="vegetable",
    kc_monthly=[
        0.70,  # Jan (coastal CA, year-round)
        0.80,  # Feb
        0.90,  # Mar (spring peak production)
        0.95,  # Apr
        1.00,  # May (peak)
        0.95,  # Jun
        0.85,  # Jul
        0.80,  # Aug
        0.80,  # Sep (fall replant)
        0.85,  # Oct
        0.75,  # Nov
        0.70,  # Dec
    ],
    peak_season_months=[4, 5, 6],
    irrigation_systems=["drip"],
    typical_tdh_ft=90,
    notes="Drip-exclusively irrigated. Ventura, Santa Cruz, Watsonville. "
          "Very high water quality requirements."
)


# ─────────────────────────────────────────────────────────────────────────────
# Master registry
# ─────────────────────────────────────────────────────────────────────────────
CROPS: Dict[str, CropProfile] = {
    "almond": ALMOND,
    "pistachio": PISTACHIO,
    "walnut": WALNUT,
    "citrus": CITRUS,
    "avocado": AVOCADO,
    "wine_grape": WINE_GRAPE,
    "table_grape": TABLE_GRAPE,
    "alfalfa": ALFALFA,
    "processing_tomato": PROCESSING_TOMATO,
    "cotton": COTTON,
    "lettuce": LETTUCE,
    "strawberry": STRAWBERRY,
}

CROP_GROUPS = {
    "Tree Crops": ["almond", "pistachio", "walnut", "citrus", "avocado"],
    "Vine Crops": ["wine_grape", "table_grape"],
    "Field Crops": ["alfalfa", "cotton"],
    "Row & Vegetable": ["processing_tomato", "lettuce", "strawberry"],
}
