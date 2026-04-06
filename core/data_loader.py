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
    # Artık doğrudan 4326 olan dosyayı okuyoruz
    path = "/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/Script/Python/climate_indices_map_tool/data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025_4326.shp"
    if not os.path.exists(path):
        return None
    return gpd.read_file(path)

@st.cache_data
def load_districts_shp():
    # Doğrudan 4326 olan ilçeler dosyası
    path = "/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/Script/Python/climate_indices_map_tool/data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm2_2025_4326.shp"
    if not os.path.exists(path):
        return None
    return gpd.read_file(path) 

def list_available_indices():
    if not os.path.exists(INDICES_DIR):
        return {}
    files = sorted([f for f in os.listdir(INDICES_DIR) if f.endswith('.tif')])
    return {get_friendly_name(f): f for f in files}