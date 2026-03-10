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
st.title("Projection & Alignment Shield")

nc_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_path) and os.path.exists(shp_path):
    # 1. VERİ YÜKLEME VE PROJEKSİYON MÜHÜRLEME
    ds = xr.open_dataset(nc_path)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: data = data.mean('time')

    # KRİTİK: Verinin EPSG:4326 olduğundan emin ol ve metadata'yı temizle
    data.rio.write_crs("EPSG:4326", inplace=True)
    
    # SHP Yükle ve Raster ile aynı projeksiyona zorla
    shp = gpd.read_file(shp_path).to_crs("EPSG:4326")

    # 2. HARİTA (Altlık harita ile birlikte)
    m = leafmap.Map(center=[39, 35], zoom=6, tiles="OpenStreetMap")

    # 3. MILIMETRIC EXTENT CALCULATION
    # Notebook'ta yaptığın pcolormesh mantığını ImageOverlay'e öğretiyoruz
    # 
    lons = data.lon.values
    lats = data.lat.values
    
    # Çözünürlük hesabı
    d_lon = (lons[1] - lons[0]) if len(lons) > 1 else 0.008333
    d_lat = (lats[1] - lats[0]) if len(lats) > 1 else -0.008333

    # Sınırları merkezden (center) köşeye (edge) çekiyoruz
    # Bu yapılmazsa SHP ile Raster arasında 500 metrelik (yarım piksel) o meşhur kayma olur.
    west, east = lons.min() - abs(d_lon)/2, lons.max() + abs(d_lon)/2
    south, north = lats.min() - abs(d_lat)/2, lats.max() + abs(d_lat)/2
    
    bnds = [[south, west], [north, east]]

    # 4. RASTER RENDER
    vmin, vmax = float(data.min()), float(data.max())
    plot_vals = data.values
    
    # Y ekseni yön kontrolü
    if lats[0] < lats[-1]:
        plot_vals = np.flipud(plot_vals)

    norm = (plot_vals - vmin) / (vmax - vmin)
    rgba = plt.get_cmap('viridis')(np.clip(norm, 0, 1))
    
    # Katmanları ekle
    ImageOverlay(image=rgba, bounds=bnds, opacity=0.7, name="Index").add_to(m)
    m.add_gdf(shp, layer_name="Boundaries", style={'color': 'red', 'fillOpacity': 0, 'weight': 1.5})

    m.to_streamlit(height=800)

    # 5. DIAGNOSTIC PRINT (Masaüstü vs Online karşılaştırması için)
    st.write("### Diagnostic Info")
    st.write(f"Data CRS: {data.rio.crs} | SHP CRS: {shp.crs}")
    st.write(f"Calculated Bounds: {bnds}")

else:
    st.error("Data folders missing!")