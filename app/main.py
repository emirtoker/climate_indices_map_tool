import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import geopandas as gpd
import os
import numpy as np
import matplotlib.pyplot as plt
import folium
from folium.raster_layers import ImageOverlay

st.set_page_config(layout="wide")
st.title("Final Solution: Fixed CRS Online Map")

# 1. YOLLAR
nc_file = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_file = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_file) and os.path.exists(shp_file):
    # 2. VERİYİ OKU VE CRS MÜHÜRLE
    ds = xr.open_dataset(nc_file)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    
    # CRS Mühürleme (Notebook'ta yaptığımızın aynısı)
    data.rio.write_crs("EPSG:4326", inplace=True)
    
    # SHP Oku
    shp = gpd.read_file(shp_file).to_crs("EPSG:4326")

    # 3. HARİTA
    m = leafmap.Map(center=[39, 35], zoom=6, tiles="OpenStreetMap")

    # 4. MİLİMETRİK BOUNDS HESABI (Manuel hesap yok, Rioxarray'e soruyoruz)
    left, bottom, right, top = data.rio.bounds()
    bnds = [[bottom, left], [top, right]]

    # 5. RENDER (ImageOverlay - Online Dostu)
    vmin, vmax = float(data.min()), float(data.max())
    vals = data.values
    
    # NetCDF yön kontrolü
    if data.lat[0] < data.lat[-1]:
        vals = np.flipud(vals)

    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    rgba = plt.get_cmap('viridis')(norm(vals))
    
    # Raster Ekle
    ImageOverlay(
        image=rgba,
        bounds=bnds,
        opacity=0.7,
        name="Climate Index"
    ).add_to(m)
    
    # SHP Ekle (Kırmızı)
    m.add_gdf(shp, layer_name="Boundaries", style={'color': 'red', 'fillOpacity': 0, 'weight': 1.5})

    # Keskin pikseller için CSS
    m.get_root().header.add_child(folium.Element("""
    <style> .leaflet-image-layer { image-rendering: pixelated !important; } </style>
    """))

    # 6. STREAMLIT'E BAS
    m.to_streamlit(height=700)

else:
    st.error("Dosyalar bulunamadı!")