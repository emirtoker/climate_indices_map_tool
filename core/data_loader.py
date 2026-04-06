import xarray as xr
import geopandas as gpd
import streamlit as st
import os
import rioxarray
import json
import base64
from config.settings import INDICES_DIR, SHP_PATH, DISTRICTS_PATH, LCZ_PNG, LCZ_META, LCZ_PATH

@st.cache_data(show_spinner="LCZ Verisi Yükleniyor...")
def load_lcz_data():
    if not os.path.exists(LCZ_PATH):
        return None, None
    
    import rioxarray
    ds = rioxarray.open_rasterio(LCZ_PATH, mask_and_scale=True)
    
    if 'band' in ds.dims:
        ds = ds.sel(band=1)
    
    # Koordinatları al
    left, bottom, right, top = ds.rio.transform_bounds("EPSG:4326")
    bounds = [[bottom, left], [top, right]]
    
    return ds, bounds

@st.cache_data
def load_stats():
    json_path = os.path.join(INDICES_DIR, "stats.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def get_friendly_name(filename):
    clean_name = filename.replace('_cog.tif', '').replace('.tif', '').replace('.nc', '')
    parts = clean_name.split('_')
    if len(parts) > 5:
        content_parts = parts[5:]
        abbr = content_parts[0].upper()
        full_name = " ".join(content_parts[1:]).upper()
        return f"{abbr} - {full_name}"
    return clean_name.upper()

# --- ADIM 1 (RAM CACHE OPTİMİZASYONU) ---
@st.cache_data(show_spinner="RAM'e yükleniyor...")
def load_index_data(file_name_or_path):
    """
    Hem sadece dosya ismini (Historical) hem de tam yolu (Future) kabul eder.
    """
    # Eğer gelen değer tam bir yolsa (Future), direkt onu kullan
    if os.path.isabs(file_name_or_path):
        path = file_name_or_path
    else:
        # Eğer sadece dosya ismiyse (Historical), INDICES_DIR ile birleştir
        path = os.path.join(INDICES_DIR, file_name_or_path)
    
    ds = rioxarray.open_rasterio(path, mask_and_scale=True)
    
    if 'band' in ds.dims:
        data = ds.isel(band=0).load().astype("float32")
    else:
        data = ds.load().astype("float32")
        
    unit = ds.attrs.get('units', 'unit')
    return data, os.path.basename(path), unit
# -------------------------------------------------------

@st.cache_data
def load_turkiye_shp():
    # Hardcoded path silindi, settings'teki yol kullanıldı
    if not os.path.exists(SHP_PATH):
        return None
    return gpd.read_file(SHP_PATH)

@st.cache_data
def load_districts_shp():
    # Hardcoded path silindi
    if not os.path.exists(DISTRICTS_PATH):
        return None
    return gpd.read_file(DISTRICTS_PATH) 

@st.cache_data
def load_lcz_static():
    if os.path.exists(LCZ_PNG) and os.path.exists(LCZ_META):
        with open(LCZ_META, "r") as f:
            meta = json.load(f)
        with open(LCZ_PNG, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/png;base64,{b64}", meta["bounds"]
    return None, None

def list_available_indices():
    if not os.path.exists(INDICES_DIR):
        return {}
    files = sorted([f for f in os.listdir(INDICES_DIR) if f.endswith('.tif')])
    return {get_friendly_name(f): f for f in files}
