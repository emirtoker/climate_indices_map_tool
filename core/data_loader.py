import xarray as xr
import geopandas as gpd
import streamlit as st
import os
import rioxarray
from config.settings import INDICES_DIR, SHP_PATH

def get_friendly_name(filename):
    """Naming rule: Skip first 5 parts (CHELSA_TR_yearly_date1_date2_...)"""
    # Hem .nc hem .tif uzantılarını temizle
    clean_name = filename.replace('.nc', '').replace('.tif', '')
    parts = clean_name.split('_')
    if len(parts) > 5:
        content_parts = parts[5:]
        abbr = content_parts[0].upper()
        full_name = " ".join(content_parts[1:]).upper()
        return f"{abbr} - {full_name}"
    return filename.upper()

@st.cache_data
def load_index_data(file_name):
    path = os.path.join(INDICES_DIR, file_name)
    
    # GeoTIFF veya NetCDF fark etmeksizin rioxarray ile açıyoruz
    # mask_and_scale=True ile NoData değerlerini otomatik NaN yapar
    ds = rioxarray.open_rasterio(path, mask_and_scale=True)
    
    # Eğer dosya NetCDF ise bazen band yapısı farklı gelebilir
    # Genelde band 1'i alıyoruz
    if hasattr(ds, 'band'):
        data = ds.sel(band=1)
    else:
        data = ds

    # Birim bilgisini al (Tif'te olmayabilir, o yüzden default 'unit')
    unit = data.attrs.get('units', 'unit')
    var_name = file_name # İsim olarak dosya adını kullanıyoruz
    
    return data, var_name, unit

@st.cache_data
def load_turkiye_shp():
    if not os.path.exists(SHP_PATH):
        return None
    # Harita motorunun beklediği standart WGS84
    return gpd.read_file(SHP_PATH).to_crs("EPSG:4326")

def list_available_indices():
    if not os.path.exists(INDICES_DIR):
        return {}
    # Öncelik .tif dosyalarında, yoksa .nc dosyalarını listele
    files = sorted([f for f in os.listdir(INDICES_DIR) if f.endswith(('.tif', '.nc'))])
    
    # Eğer aynı dosyanın hem .tif hem .nc'si varsa, .tif olanı tercih et
    unique_files = {}
    for f in files:
        base = f.rsplit('.', 1)[0]
        if f.endswith('.tif') or base not in unique_files:
            unique_files[base] = f
            
    return {get_friendly_name(f): f for f in unique_files.values()}