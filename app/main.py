import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import geopandas as gpd
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import branca.colormap as cm
import folium
from folium.raster_layers import ImageOverlay

st.set_page_config(layout="wide", page_title="Online Diagnostic Test")
st.title("Diagnostic Interactive Test (Online Mode)")

# 1. DOSYA YOLLARI - GitHub reposundaki yapıya göre (root'tan itibaren)
nc_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

# Dosya yollarını kontrol et ve ekrana yazdır (Debug için)
nc_exists = os.path.exists(nc_path)
shp_exists = os.path.exists(shp_path)

if nc_exists and shp_exists:
    # 2. VERİ YÜKLEME
    ds = xr.open_dataset(nc_path)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: 
        data = data.mean('time')
    
    # Koordinat isimlerini otomatik algıla
    lon_n = 'lon' if 'lon' in data.coords else ('x' if 'x' in data.coords else 'longitude')
    lat_n = 'lat' if 'lat' in data.coords else ('y' if 'y' in data.coords else 'latitude')
    
    # SHP Yükle
    shp = gpd.read_file(shp_path)
    
    # 3. SIDEBAR (Kontrol Paneli)
    st.sidebar.header("Map Settings")
    cmap_choice = st.sidebar.selectbox("Color Palette", ["viridis", "Spectral_r", "RdYlBu_r", "magma", "plasma"])
    alpha_val = st.sidebar.slider("Opacity", 0.0, 1.0, 0.7)
    
    # 4. HARİTA MOTORU
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)
    
    # CSS: Piksellerin keskin görünmesi için mühür
    m.get_root().header.add_child(folium.Element("""
    <style> .leaflet-image-layer { image-rendering: pixelated !important; } </style>
    """))

    # SHP Katmanı (Sınırlar)
    m.add_gdf(shp, layer_name="Türkiye Boundaries", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.0})

    # 5. RASTER TO IMAGEOVERLAY (Milimetrik Hizalama Hesabı)
    # [Image of pixel alignment in GIS data comparing center and corner coordinates]
    x_min, x_max = float(data[lon_n].min()), float(data[lon_n].max())
    y_min, y_max = float(data[lat_n].min()), float(data[lat_n].max())
    
    # Çözünürlük hesabı (n-1 kuralı ile tam köşe sınırları)
    res_x = (x_max - x_min) / (data.shape[1] - 1)
    res_y = (y_max - y_min) / (data.shape[0] - 1)
    
    # Bounds: [[South, West], [North, East]] - Yarım piksel kaydırmalı (Corner alignment)
    bnds = [[y_min - abs(res_y)/2, x_min - abs(res_x)/2], 
            [y_max + abs(res_y)/2, x_max + abs(res_x)/2]]
    
    # Render için Normalizasyon
    vmin, vmax = float(data.min()), float(data.max())
    vals = data.values
    norm = (vals - vmin) / (vmax - vmin)
    norm = np.clip(norm, 0, 1)
    
    # Renk paleti uygula
    cmap = plt.get_cmap(cmap_choice)
    rgba = cmap(norm)
    rgba = np.flipud(rgba) # NetCDF eksenini haritaya uydur
    
    # Katmanı ekle
    ImageOverlay(image=rgba, bounds=bnds, opacity=alpha_val, name="Climate Index Layer").add_to(m)

    # 6. COLORBAR (Branca)
    colors = [mpl.colors.rgb2hex(cmap(i)) for i in np.linspace(0, 1, 256)]
    cmap_obj = cm.LinearColormap(colors=colors, vmin=vmin, vmax=vmax, caption=f"{var_name} Index")
    m.add_child(cmap_obj)

    # Haritayı bas
    m.to_streamlit(height=800)
    
    # Bilgi mesajı
    st.success(f"Successfully rendered {var_name}")
    st.write(f"Grid: {data.shape} | NC Bounds: {x_min:.4f}, {y_min:.4f} to {x_max:.4f}, {y_max:.4f}")

else:
    st.error("FILES NOT FOUND IN REPOSITORY!")
    st.write(f"NC Path ({nc_path}): {'✅ Found' if nc_exists else '❌ Missing'}")
    st.write(f"SHP Path ({shp_path}): {'✅ Found' if shp_exists else '❌ Missing'}")
    st.write("Current working directory:", os.getcwd())
    st.write("Directory contents:", os.listdir(".") if os.path.exists(".") else "Cannot access root")