"""
config/settings.py

Central configuration for paths and constants used across the application.

All paths are derived from BASE_DIR (the project root). This keeps the
app portable: clone the repo anywhere, paths still resolve correctly.

LAYOUT
------
    climate_indices_map_tool/
    ├── app/
    ├── config/
    │   └── settings.py     <-- this file
    ├── core/
    ├── data/
    │   ├── indices/
    │   │   ├── historical/     (64 COG TIFFs)
    │   │   ├── future/
    │   │   │   ├── ssp126/     (128 COG TIFFs)
    │   │   │   ├── ssp245/     (128 COG TIFFs)
    │   │   │   └── ssp585/     (128 COG TIFFs)
    │   │   └── stats.json      (central stats for all 448 files)
    │   ├── shapefiles/
    │   ├── lcz/
    │   └── topography/
    ├── utils/
    │   └── indices_catalog.py  <-- catalog source of truth
    └── viz/
"""

import os

# ---------------------------------------------------------------------------
# Project root (derived from this file's location)
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


# ---------------------------------------------------------------------------
# Climate indices — COG TIFF outputs
# ---------------------------------------------------------------------------

# Root of all index outputs
INDICES_DIR = os.path.join(DATA_DIR, "indices")

# Historical (CHELSA observed climatology)
INDICES_DIR_HISTORICAL = os.path.join(INDICES_DIR, "historical")

# Future (CHELSA + GCMs ensemble, projected climatology)
INDICES_DIR_FUTURE = os.path.join(INDICES_DIR, "future")

# Scenario subdirectories under FUTURE
INDICES_DIR_FUTURE_SSP126 = os.path.join(INDICES_DIR_FUTURE, "ssp126")
INDICES_DIR_FUTURE_SSP245 = os.path.join(INDICES_DIR_FUTURE, "ssp245")
INDICES_DIR_FUTURE_SSP585 = os.path.join(INDICES_DIR_FUTURE, "ssp585")

# Convenient mapping: scenario name -> directory
FUTURE_SCENARIOS = {
    "ssp126": INDICES_DIR_FUTURE_SSP126,
    "ssp245": INDICES_DIR_FUTURE_SSP245,
    "ssp585": INDICES_DIR_FUTURE_SSP585,
}

# Central stats.json (one file for all 448 indices)
STATS_PATH = os.path.join(INDICES_DIR, "stats.json")


# ---------------------------------------------------------------------------
# Shapefiles (Türkiye administrative boundaries, EPSG:4326)
# ---------------------------------------------------------------------------

SHP_DIR = os.path.join(DATA_DIR, "shapefiles", "tur_adm_2025_ab_shp")

# Province-level (ADM1)
SHP_PATH = os.path.join(SHP_DIR, "tur_admbnda_adm1_2025_4326.shp")

# District-level (ADM2)
DISTRICTS_PATH = os.path.join(SHP_DIR, "tur_admbnda_adm2_2025_4326.shp")


# ---------------------------------------------------------------------------
# LCZ (Local Climate Zones)
# ---------------------------------------------------------------------------

LCZ_DIR = os.path.join(DATA_DIR, "lcz")
LCZ_PATH = os.path.join(LCZ_DIR, "lcz_turkey_1km.tif")
LCZ_PNG = os.path.join(LCZ_DIR, "lcz_render.png")
LCZ_META = os.path.join(LCZ_DIR, "lcz_metadata.json")


# ---------------------------------------------------------------------------
# Topography
# ---------------------------------------------------------------------------

TOPOGRAPHY_PATH = os.path.join(DATA_DIR, "topography", "topography_tr.nc")


# ---------------------------------------------------------------------------
# Map defaults
# ---------------------------------------------------------------------------

MAP_DEFAULT_CENTER = [38.9, 35.5]  # Türkiye center (lat, lon)
MAP_DEFAULT_ZOOM = 5

# Approximate Türkiye bounding box for tile reads (EPSG:4326)
TR_BBOX = {
    "min_lat": 35.7,
    "max_lat": 42.3,
    "min_lon": 25.3,
    "max_lon": 45.0,
}