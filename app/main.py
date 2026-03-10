import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import os
import matplotlib.pyplot as plt
import numpy as np
from folium.raster_layers import ImageOverlay

st.set_page_config(layout="wide")
st.title("Streamlit Cloud - Stable Fix")

test_file = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"

if os.path.exists(test_file):
    # 1. Data Loading
    ds = xr.open_dataset(test_file)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()

    # Koordinat isimlerini otomatik bul (lat/lon veya x/y fark etmez)
    lat_name = 'lat' if 'lat' in data.coords else ('y' if 'y' in data.coords else None)
    lon_name = 'lon' if 'lon' in data.coords else ('x' if 'x' in data.coords else None)

    if lat_name and lon_name:
        # 2. Image Preparation (Manual RGBA conversion to bypass GDAL)
        # Veriyi 0-1 arasına normalize et
        d_min, d_max = float(data.min()), float(data.max())
        norm_data = (data - d_min) / (d_max - d_min)
        
        # Renk paletini uygula
        cmap = plt.get_cmap('viridis')
        rgba_data = cmap(norm_data)
        rgba_data = np.flipud(rgba_data)

        # Koordinat sınırlarını belirle
        bounds = [[float(data[lat_name].min()), float(data[lon_name].min())], 
                  [float(data[lat_name].max()), float(data[lon_name].max())]]

        # 3. Map Rendering
        # Tiles=None diyerek altlığı kapatıyoruz (daha hızlı ve temiz)
        m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)
        
        # Veriyi 'Image' olarak haritaya bas
        ImageOverlay(
            image=rgba_data,
            bounds=bounds,
            opacity=0.8,
            name="Raster Layer"
        ).add_to(m)

        m.to_streamlit(height=600)
        st.write(f"Displaying: {var_name} ({d_min:.2f} to {d_max:.2f})")
    else:
        st.error(f"Koordinatlar bulunamadı. Mevcut koordinatlar: {list(data.coords)}")