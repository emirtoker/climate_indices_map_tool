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
st.title("Full Projection Alignment (EPSG:4326 Sync)")

# 1. DOSYA YOLLARI
nc_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_path) and os.path.exists(shp_path):
    # 2. VERİ OKUMA VE PROJEKSİYON ZORLAMA
    ds = xr.open_dataset(nc_path)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: data = data.mean('time')

    # KRİTİK: Verinin projeksiyonunu mühürle (rioxarray gerektirir)
    # Eğer metadata bozuksa bunu manuel EPSG:4326 yapar
    if not hasattr(data, 'rio'):
        st.error("rioxarray kütüphanesi eksik! Projeksiyon yapılamıyor.")
        st.stop()
    
    data.rio.write_crs("EPSG:4326", inplace=True)
    
    # SHP Yükle ve Raster ile aynı projeksiyona getir
    shp = gpd.read_file(shp_path).to_crs("EPSG:4326")
    
    # 3. HARİTA (Arka plan yok, sadece veri)
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)

    # 4. COORDINATE EXTRACTION (Direct from Rioxarray)
    # bounds = [west, south, east, north]
    bounds_rio = data.rio.bounds()
    
    # Folium Format: [[south, west], [north, east]]
    bnds = [[bounds_rio[1], bounds_rio[0]], [bounds_rio[3], bounds_rio[2]]]

    # 5. RENDER
    vmin, vmax = float(data.min()), float(data.max())
    plot_data = data.values
    
    # NetCDF verileri genellikle yukarıdan aşağıya dizilir, 
    # ImageOverlay için yön kontrolü şart:
    if data.lat[0] < data.lat[-1]:
        plot_data = np.flipud(plot_data)

    norm = (plot_data - vmin) / (vmax - vmin)
    rgba = plt.get_cmap('viridis')(np.clip(norm, 0, 1))
    
    # KATMANLAR
    # Raster
    ImageOverlay(image=rgba, bounds=bnds, opacity=0.8, name="Aligned Raster").add_to(m)
    # SHP (Kırmızı çizgiler)
    m.add_gdf(shp, layer_name="Admin Boundaries", style={'color': 'red', 'fillOpacity': 0, 'weight': 1.5})

    m.to_streamlit(height=800)

    # TEŞHİS BİLGİSİ
    st.write("### Teşhis Ekranı (RioXarray Focus)")
    st.write(f"RIO Bounds: {bounds_rio}")
    st.write(f"Calculated Folium Bounds: {bnds}")
    st.write(f"Raster CRS: {data.rio.crs}")
    st.write(f"SHP CRS: {shp.crs}")

else:
    st.error("Dosyalar bulunamadı!")