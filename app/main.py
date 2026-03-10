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
st.title("Milimetrik Raster-SHP Alignment")

# 1. DOSYA YOLLARI
nc_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_path) and os.path.exists(shp_path):
    # 2. VERİ OKUMA
    ds = xr.open_dataset(nc_path)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: data = data.mean('time')
    
    shp = gpd.read_file(shp_path)
    
    # 3. HARİTA (Arka planı sildim, tertemiz siyah/beyaz boşluk)
    # tiles=None yaparak sadece senin verilerini göreceğiz
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)

    # 4. KRİTİK HİZALAMA (Notebook'taki pcolormesh mantığı)
    lons = data.lon.values
    lats = data.lat.values
    
    # Çözünürlük hesabı (merkezler arası mesafe)
    d_lon = (lons[-1] - lons[0]) / (len(lons) - 1)
    d_lat = (lats[-1] - lats[0]) / (len(lats) - 1)
    
    # Birebir örtüşme için: Piksel merkezinden dış sınıra yarım piksel kaydırıyoruz
    # Folium Bounds formatı: [[min_lat, min_lon], [max_lat, max_lon]]
    south = lats.min() - abs(d_lat)/2
    north = lats.max() + abs(d_lat)/2
    west = lons.min() - abs(d_lon)/2
    east = lons.max() + abs(d_lon)/2
    
    bnds = [[south, west], [north, east]]

    # 5. RASTER RENDER
    vmin, vmax = float(data.min()), float(data.max())
    plot_data = data.values
    
    # Enlemler (lat) NetCDF'de genellikle yukarıdan aşağıya (descending) olur.
    # Eğer harita ters çıkarsa burası düzeltecek:
    if lats[0] < lats[-1]:
        plot_data = np.flipud(plot_data)

    norm = (plot_data - vmin) / (vmax - vmin)
    rgba = plt.get_cmap('viridis')(np.clip(norm, 0, 1))
    
    # Raster'ı bas
    ImageOverlay(image=rgba, bounds=bnds, opacity=0.8, name="Raster").add_to(m)
    
    # SHP'yi Raster'ın ÜSTÜNE bas (Kırmızı yaparak çakışmayı görelim)
    m.add_gdf(shp, layer_name="SHP", style={'color': 'red', 'fillOpacity': 0, 'weight': 1.5})

    # Keskin piksel CSS mühürü
    m.get_root().header.add_child(folium.Element("""
    <style> .leaflet-image-layer { image-rendering: pixelated !important; } </style>
    """))

    m.to_streamlit(height=800)

    # Teşhis Bilgileri
    st.write("### Teşhis Ekranı")
    st.write(f"Veri Boyutu: {data.shape}")
    st.write(f"Hesaplanan Sınırlar: {bnds}")
    st.write(f"Çözünürlük (d_lat, d_lon): {d_lat:.6f}, {d_lon:.6f}")

else:
    st.error("Dosyalar bulunamadı!")