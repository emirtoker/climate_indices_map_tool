"""
core/data_loader.py

Cached data loaders for the Streamlit app.

WHAT'S HERE
-----------
- Raster loaders for climate index COG TIFFs (via IndexFile)
- LCZ raster + static PNG legend
- Türkiye administrative boundary shapefiles (province + district)

WHAT MOVED OUT (vs the old version)
-----------------------------------
- `get_friendly_name()`, `list_available_indices()`, `load_stats()`:
  these are now handled by `utils.naming` (which merges catalog + stats
  into IndexFile objects). The sidebar should call `load_all_index_files()`
  from utils.naming, not anything here.

USAGE
-----
    from utils.naming import load_all_index_files
    from core.data_loader import load_raster_for_index

    files = load_all_index_files()
    pcd_hist = [f for f in files if f.catalog_code == "PCD" and f.kind == "historical"][0]
    data, meta = load_raster_for_index(pcd_hist)
"""

import base64
import json
import os

import geopandas as gpd
import rioxarray
import streamlit as st

from config.settings import (
    SHP_PATH,
    DISTRICTS_PATH,
    LCZ_PATH,
    LCZ_PNG,
    LCZ_META,
)
from utils.naming import IndexFile


# ---------------------------------------------------------------------------
# Climate index rasters — IndexFile-based loader
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Loading raster...")
def load_raster_for_index(_index_file: IndexFile):
    """
    Open the COG TIFF for a given IndexFile and return its data + metadata.

    Streamlit caches by argument value; the leading underscore on the param
    name tells Streamlit to use object id (not deep-hash the dataclass).
    For this to work safely, the SAME IndexFile instance should be passed
    on every rerun — which is exactly how we use it from the sidebar.

    Returns:
        data            : xarray.DataArray (float32, single band, no 'band' dim)
        meta            : dict with keys:
                            - filename
                            - unit              (from catalog)
                            - long_name         (from catalog)
                            - display_label     (from IndexFile)
                            - stat_min, stat_max  (from stats.json)
                            - bounds_4326       (list of [[bottom, left], [top, right]])
    """
    if not os.path.exists(_index_file.path):
        raise FileNotFoundError(f"TIF not found: {_index_file.path}")

    ds = rioxarray.open_rasterio(_index_file.path, mask_and_scale=True)

    if "band" in ds.dims:
        data = ds.isel(band=0).load().astype("float32")
    else:
        data = ds.load().astype("float32")

    # Compute folium-friendly bounds [[bottom, left], [top, right]]
    left, bottom, right, top = data.rio.transform_bounds("EPSG:4326")
    bounds_4326 = [[bottom, left], [top, right]]

    meta = {
        "filename":      _index_file.filename,
        "unit":          _index_file.unit,
        "long_name":     _index_file.long_name,
        "display_label": _index_file.display_label,
        "stat_min":      _index_file.stat_min,
        "stat_max":      _index_file.stat_max,
        "bounds_4326":   bounds_4326,
    }
    return data, meta


# ---------------------------------------------------------------------------
# LCZ (Local Climate Zones)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Loading LCZ raster...")
def load_lcz_data():
    """Open the 1km LCZ raster. Returns (DataArray, folium-bounds) or (None, None)."""
    if not os.path.exists(LCZ_PATH):
        return None, None

    ds = rioxarray.open_rasterio(LCZ_PATH, mask_and_scale=True)
    if "band" in ds.dims:
        ds = ds.sel(band=1)

    left, bottom, right, top = ds.rio.transform_bounds("EPSG:4326")
    bounds = [[bottom, left], [top, right]]
    return ds, bounds


@st.cache_data
def load_lcz_static():
    """Load the pre-rendered LCZ PNG (base64 data URI) + bounds.
    Returns (data_uri, bounds) or (None, None) if files are missing.
    Faster than rendering the raster live; used as default LCZ layer.
    """
    if not (os.path.exists(LCZ_PNG) and os.path.exists(LCZ_META)):
        return None, None

    with open(LCZ_META, "r") as f:
        meta = json.load(f)
    with open(LCZ_PNG, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{b64}", meta["bounds"]


# ---------------------------------------------------------------------------
# Administrative boundaries (shapefiles)
# ---------------------------------------------------------------------------

@st.cache_data
def load_turkiye_shp():
    """ADM1 (province-level) boundaries, EPSG:4326."""
    if not os.path.exists(SHP_PATH):
        return None
    return gpd.read_file(SHP_PATH)


@st.cache_data
def load_districts_shp():
    """ADM2 (district-level) boundaries, EPSG:4326."""
    if not os.path.exists(DISTRICTS_PATH):
        return None
    return gpd.read_file(DISTRICTS_PATH)