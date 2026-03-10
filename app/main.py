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

st.set_page_config(layout="wide", page_title="Coordinate Alignment Fix")
st.title("Final Diagnostic: Raster + SHP Overlay")

nc_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_path) and os.path.exists(shp_path):
    # 1. VERİ YÜKLEME
    ds = xr.open_dataset(nc_path)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: data = data.mean('time')
    
    # SHP Yükle
    shp = gpd.read_file(shp_path)
    
    # 2. HARİTA AYARI (Arka planı tamamen siliyoruz)
    # tiles=None yaparak sadece senin verilerini göreceğiz
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)

    # 3. MİLİMETRİK BOUNDS HESABI
    # Veri merkez noktaları (Piksel merkezleri)
    lons = data.lon.values
    lats = data.lat.values
    
    # Çözünürlük (Her bir pikselin genişliği ve yüksekliği)
    res_x = (lons[-1] - lons[0]) / (len(lons) - 1)
    res_y = (lats[-1] - lats[0]) / (len(lats) - 1)
    
    # Folium'un resmi tam oturtması için dış sınırları hesaplıyoruz (Corner-to-Corner)
    # Merkezden yarım piksel dışarı esnetme:
    west = lons.min() - (abs(res_x) / 2)
    east = lons.max() + (abs(res_x) / 2)
    south = lats.min() - (abs(res_y) / 2)
    north = lats.max() + (abs(res_y) / 2)
    
    bnds = [[south, west], [north, east]]

    # 4. RASTER RENDER
    vmin, vmax = float(data.min()), float(data.max())
    plot_data = data.values
    
    # Koordinat yönü kontrolü (Y ekseni tersse düzelt)
    if lats[0] < lats[-1]:
        plot_data = np.flipud(plot_data)
        
    norm = (plot_data - vmin) / (vmax - vmin)
    norm = np.clip(norm, 0, 1)
    
    cmap = plt.get_cmap('viridis')
    rgba = cmap(norm)
    
    # Raster katmanını ekle
    ImageOverlay(
        image=rgba, 
        bounds=bnds, 
        opacity=0.8, 
        name="Climate Raster"
    ).add_to(m)

    # 5. SHP KATMANI (Raster'ın üstüne çiziyoruz)
    # Bu katman raster ile tam örtüşmeli
    m.add_gdf(
        shp, 
        layer_name="TR Boundaries", 
        style={'color': 'red', 'fillOpacity': 0, 'weight': 1.5} # Kırmızı yaparak hatayı görelim
    )

    # Keskin pikseller için CSS
    m.get_root().header.add_child(folium.Element("""
    <style> .leaflet-image-layer { image-rendering: pixelated !important; } </style>
    """))

    m.to_streamlit(height=800)

    # DEBUG ÇIKTILARI
    st.write("### Diagnostics")
    st.write(f"Calculated Bounds (S,W,N,E): {south}, {west}, {north}, {east}")
    st.write(f"Data Shape: {data.shape} | Var: {var_name}")

else:
    st.error("Dosyalar bulunamadı!")