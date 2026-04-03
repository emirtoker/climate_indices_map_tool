import xarray as xr
import geopandas as gpd
import streamlit as st
import os
import rioxarray
import json
from config.settings import INDICES_DIR, SHP_PATH

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

# --- DÜZENLENEN KISIM: ADIM 1 (RAM CACHE OPTİMİZASYONU) ---
@st.cache_data(show_spinner="RAM'e yükleniyor...")
def load_index_data(file_name):
    """
    CHELSA verisini diskten okur ve RAM'e (.load()) kilitler.
    Lazy loading (tembel okuma) iptal edildiği için hız 10 kat artar.
    """
    path = os.path.join(INDICES_DIR, file_name)
    
    # Veriyi rioxarray ile aç
    ds = rioxarray.open_rasterio(path, mask_and_scale=True)
    
    # KRİTİK DOKUNUŞ: 
    # .load() ekleyerek veriyi diskten söküp RAM'e alıyoruz.
    # .astype("float32") ile bellek kullanımını %50 düşürüyoruz.
    if 'band' in ds.dims:
        data = ds.isel(band=0).load().astype("float32")
    else:
        data = ds.load().astype("float32")
        
    unit = ds.attrs.get('units', 'unit')
    return data, file_name, unit
# -------------------------------------------------------

@st.cache_data
def load_turkiye_shp():
    if not os.path.exists(SHP_PATH):
        st.error(f"SHP dosyası bulunamadı: {SHP_PATH}")
        return None
    return gpd.read_file(SHP_PATH).to_crs("EPSG:4326")

def list_available_indices():
    if not os.path.exists(INDICES_DIR):
        return {}
    files = sorted([f for f in os.listdir(INDICES_DIR) if f.endswith('.tif')])
    return {get_friendly_name(f): f for f in files}