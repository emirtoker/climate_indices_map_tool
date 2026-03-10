import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import geopandas as gpd
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import branca.colormap as cm
from folium.raster_layers import ImageOverlay

st.set_page_config(layout="wide")
st.title("Diagnostic Interactive Test (Milimetric Alignment)")

# 1. DOSYA YOLLARI
base_path = os.path.expanduser("~/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/Script/Python/climate_indices_map_tool")
nc_path = os.path.join(base_path, "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc")
shp_path = os.path.join(base_path, "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp")

if os.path.exists(nc_path) and os.path.exists(shp_path):
    # 2. VERİ YÜKLEME
    ds = xr.open_dataset(nc_path)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: data = data.mean('time')
    
    shp = gpd.read_file(shp_path)
    
    # 3. SIDEBAR (Sadece Colorbar Seçimi)
    st.sidebar.header("Settings")
    cmap_choice = st.sidebar.selectbox("Color Palette", ["viridis", "Spectral_r", "RdYlBu_r", "magma", "plasma"])
    alpha_val = st.sidebar.slider("Opacity", 0.0, 1.0, 0.7)
    
    # 4. HARİTA MOTORU
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)
    
    # CSS: Pixelated rendering (Keskin pikseller)
    m.get_root().header.add_child(mpl.backend_bases.folium.Element("""
    <style> .leaflet-image-layer { image-rendering: pixelated !important; } </style>
    """))

    # SHP Katmanı (Siyah İnce Sınırlar)
    m.add_gdf(shp, layer_name="Boundaries", style={'color': 'black', 'fillOpacity': 0, 'weight': 0.8})

    # 5. RASTER TO IMAGEOVERLAY (Notebook'taki hizalamayı buraya taşıyoruz)
    lon_n = 'lon' if 'lon' in data.coords else ('x' if 'x' in data.coords else 'longitude')
    lat_n = 'lat' if 'lat' in data.coords else ('y' if 'y' in data_arr.coords else 'latitude')
    
    # Notebook'taki o milimetrik extent mantığı
    x_min, x_max = float(data[lon_n].min()), float(data[lon_n].max())
    y_min, y_max = float(data[lat_n].min()), float(data[lat_n].max())
    
    # Piksel çözünürlüğüne göre sınırları köşeye (edge) çekiyoruz
    res_x = (x_max - x_min) / (data.shape[1] - 1)
    res_y = (y_max - y_min) / (data.shape[0] - 1)
    
    # Folium Bounds: [[South, West], [North, East]]
    bnds = [[y_min - res_y/2, x_min - res_x/2], [y_max + res_y/2, x_max + res_x/2]]
    
    # Normalizasyon ve Renklendirme
    vmin, vmax = float(data.min()), float(data.max())
    norm = (data.values - vmin) / (vmax - vmin)
    norm = np.clip(norm, 0, 1)
    
    cmap = plt.get_cmap(cmap_choice)
    rgba = cmap(norm)
    rgba = np.flipud(rgba) # Kuzeyi yukarı al
    
    # Haritaya bas
    ImageOverlay(image=rgba, bounds=bnds, opacity=alpha_val, name="Climate Index").add_to(m)

    # 6. COLORBAR (Branca)
    colors = [mpl.colors.rgb2hex(cmap(i)) for i in np.linspace(0, 1, 256)]
    cmap_obj = cm.LinearColormap(colors=colors, vmin=vmin, vmax=vmax, caption=f"{var_name} Index")
    m.add_child(cmap_obj)

    # Haritayı ekrana bas
    m.to_streamlit(height=800)
    
    st.write(f"Diagnostic Info: NC Range [{vmin:.2f}, {vmax:.2f}] | Bounds: {bnds}")
else:
    st.error("Dosyalar bulunamadı! Lütfen base_path ayarını kontrol et.")