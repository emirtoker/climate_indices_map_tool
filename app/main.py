import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import os
import matplotlib.pyplot as plt
import numpy as np
from folium.raster_layers import ImageOverlay
import geopandas as gpd

st.set_page_config(layout="wide")
st.title("Streamlit Cloud - Raster & Province Integration")

# Dosya Yolları
test_file = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
adm1_shp = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp" # Şehir (Province) sınırları

if os.path.exists(test_file):
    # 1. Veri Hazırlama (NC)
    ds = xr.open_dataset(test_file)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()

    lat_name = 'lat' if 'lat' in data.coords else ('y' if 'y' in data.coords else None)
    lon_name = 'lon' if 'lon' in data.coords else ('x' if 'x' in data.coords else None)

    if lat_name and lon_name:
        # RGBA Dönüşümü ve Flip (Tepetaklak düzeltmesi)
        d_min, d_max = float(data.min()), float(data.max())
        norm_data = (data - d_min) / (d_max - d_min)
        cmap = plt.get_cmap('viridis')
        rgba_data = cmap(norm_data)
        rgba_data = np.flipud(rgba_data) 

        # Sınırlar
        bounds = [[float(data[lat_name].min()), float(data[lon_name].min())], 
                  [float(data[lat_name].max()), float(data[lon_name].max())]]

        # 2. Harita Kurulumu
        m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)
        
        # A) RASTER KATMANI (Altta kalmalı)
        ImageOverlay(
            image=rgba_data,
            bounds=bounds,
            opacity=0.8,
            name="Raster Layer"
        ).add_to(m)

        # B) ŞEHİR (PROVINCE) SINIRLARI (Üstte kalmalı)
        if os.path.exists(adm1_shp):
            city_gdf = gpd.read_file(adm1_shp)
            # Şehir sınırlarını ince siyah çizgilerle çiziyoruz
            m.add_gdf(city_gdf, layer_name="Türkiye Provinces", 
                      style={'color': 'black', 'weight': 0.8, 'fillOpacity': 0})
        else:
            st.warning(f"Province SHP bulunamadı: {adm1_shp}")

        m.to_streamlit(height=700)
    else:
        st.error("Koordinatlar saptanamadı.")