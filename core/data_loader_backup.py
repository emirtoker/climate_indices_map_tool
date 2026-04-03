import xarray as xr
import geopandas as gpd
import rioxarray
import streamlit as st
import os
import numpy as np
from config.settings import INDICES_DIR, SHP_PATH

def get_friendly_name(filename):
    """Naming rule: Skip first 5 parts (CHELSA_TR_yearly_date1_date2_...)"""
    clean_name = filename.replace('.nc', '')
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
    ds = xr.open_dataset(path, mask_and_scale=True)
    var_name = list(ds.data_vars)[0]
    unit = ds[var_name].attrs.get('units', 'unit')
    
    data = ds[var_name].mean(dim='time') if 'time' in ds.dims else ds[var_name]
    
    if 'longitude' in data.coords: data = data.rename({'longitude': 'x', 'latitude': 'y'})
    elif 'lon' in data.coords: data = data.rename({'lon': 'x', 'lat': 'y'})
    
    data = data.rio.write_crs("EPSG:4326")
    shp = gpd.read_file(SHP_PATH).to_crs("EPSG:4326")
    data = data.rio.clip(shp.geometry, shp.crs, drop=True, all_touched=False)
    data.rio.write_nodata(np.nan, inplace=True)
    
    return data, var_name, unit

@st.cache_data
def load_turkiye_shp():
    if not os.path.exists(SHP_PATH): return None
    return gpd.read_file(SHP_PATH).to_crs("EPSG:4326")

def list_available_indices():
    files = sorted([f for f in os.listdir(INDICES_DIR) if f.endswith('.nc')])
    return {get_friendly_name(f): f for f in files}