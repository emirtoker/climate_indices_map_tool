import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import geopandas as gpd
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import folium
from folium.raster_layers import ImageOverlay

st.set_page_config(layout="wide")
st.title("Interactive Alignment Check (Axis Fix)")

nc_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_path) and os.path.exists(shp_path):
    # 1. VERİ OKUMA
    ds = xr.open_dataset(nc_path)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: data = data.mean('time')
    
    # SHP'yi Raster ile aynı sisteme zorla (Notebook'taki gibi)
    shp = gpd.read_file(shp_path).to_crs("EPSG:4326")

    # 2. HARİTA (Arka planı siliyoruz ki sadece çakışmayı görelim)
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)

    # 3. VERİ DİZİLİMİ VE BOUNDS (EN KRİTİK NOKTA)
    # Rioxarray'den ham sınırları alıyoruz (Elle ayar yok)
    bounds_rio = data.rio.bounds() # [west, south, east, north]
    bnds = [[bounds_rio[1], bounds_rio[0]], [bounds_rio[3], bounds_rio[2]]]
    
    # Resim verisini al
    vals = data.values
    
    # Folium ImageOverlay resmin sol üstten başladığını varsayar.
    # Eğer enlemler (lat) azalan sıradaysa (Kuzeyden Güneye), flip yapmamız gerekir.
    # Bu ayar yapılmazsa resim haritaya "ters" veya "kayık" oturur.
    lat_values = data.lat.values
    if lat_values[0] > lat_values[-1]:
        # Enlemler azalıyorsa (Standart NetCDF), veriyi dikeyde ters çevir
        vals = np.flipud(vals)

    # 4. RENDER
    vmin, vmax = float(data.min()), float(data.max())
    norm = (vals - vmin) / (vmax - vmin)
    rgba = plt.get_cmap('viridis')(np.clip(norm, 0, 1))
    
    # Raster Katmanı
    ImageOverlay(image=rgba, bounds=bnds, opacity=0.8, name="Corrected Raster").add_to(m)
    
    # SHP Katmanı (Raster'ın tam üstüne oturmalı)
    m.add_gdf(shp, layer_name="SHP Boundaries", style={'color': 'red', 'fillOpacity': 0, 'weight': 1.5})

    m.to_streamlit(height=800)

    # 5. DIAGNOSTICS
    st.write("### Diagnostics")
    st.write(f"Lat Orientation: {'Descending (North to South)' if lat_values[0] > lat_values[-1] else 'Ascending'}")
    st.write(f"Bounds: {bnds}")

else:
    st.error("Dosyalar eksik!")