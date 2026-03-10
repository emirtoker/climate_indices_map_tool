import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import geopandas as gpd
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import folium

st.set_page_config(layout="wide", page_title="Online Diagnostic Test")
st.title("Diagnostic Interactive Test (Native Coordinates)")

# 1. DOSYA YOLLARI
nc_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_path) and os.path.exists(shp_path):
    # 2. VERİ YÜKLEME
    ds = xr.open_dataset(nc_path)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: data = data.mean('time')
    
    # CRS Tanımlama (Zaten 4326 ama mühürleyelim)
    if data.rio.crs is None:
        data.rio.write_crs("EPSG:4326", inplace=True)
    
    shp = gpd.read_file(shp_path)
    
    # 3. SIDEBAR
    cmap_choice = st.sidebar.selectbox("Color Palette", ["viridis", "Spectral_r", "RdYlBu_r", "magma"])
    alpha_val = st.sidebar.slider("Opacity", 0.0, 1.0, 0.7)
    
    # 4. HARİTA MOTORU
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)
    
    # SHP Katmanı (Siyah Sınırlar)
    m.add_gdf(shp, layer_name="Türkiye Boundaries", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.0})

    # 5. NATIVE RASTER RENDERING (Kaymayı bitiren asıl yöntem)
    # Artık ImageOverlay ile resim germiyoruz. 
    # add_raster fonksiyonu verinin içindeki koordinatları (lat/lon) tek tek okur.
    
    cmap = plt.get_cmap(cmap_choice)
    # Paletteyi Branca/Folium'un anlayacağı hex listesine çevir
    palette = [mpl.colors.rgb2hex(cmap(i)) for i in np.linspace(0, 1, 256)]
    
    m.add_raster(
        data, 
        layer_name="Climate Index", 
        palette=palette, 
        opacity=alpha_val,
        nodata=np.nan
    )

    # 6. ESTETİK (Custom CSS)
    m.get_root().header.add_child(folium.Element("""
    <style> .leaflet-raster-layer { image-rendering: pixelated !important; } </style>
    """))

    m.to_streamlit(height=800)
    
    st.success(f"Rendered using native coordinates: {var_name}")
    st.write(f"CRS: {data.rio.crs} | Shape: {data.shape}")

else:
    st.error("FILES NOT FOUND!")