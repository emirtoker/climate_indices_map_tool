import streamlit as st
import leafmap.foliumap as leafmap
import rioxarray
import geopandas as gpd
import os
import numpy as np
import matplotlib.pyplot as plt
from folium.raster_layers import ImageOverlay
import folium

import os
import streamlit as st

st.write("### Sunucu Dosya Sistemi Kontrolü")
base_path = "data/indices/historical/climatology/1km/CHELSA/"
if os.path.exists(base_path):
    st.write(f"Klasör bulundu: {base_path}")
    st.write("İçindeki dosyalar:", os.listdir(base_path))
else:
    st.error(f"KLASÖR BULUNAMADI: {base_path}")
    # Root'ta ne var bakalım
    st.write("Root dizini:", os.listdir("."))
    
st.set_page_config(layout="wide")
st.title("GeoTIFF & SHP Alignment Test (QGIS Style)")

# 1. YOLLAR (Uzantıyı .tif yaptık)
tif_file = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.tif"
shp_file = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(tif_file) and os.path.exists(shp_file):
    # 2. VERİ OKUMA VE REPROJECT (QGIS'in yaptığı işi manuel yapıyoruz)
    # Tif dosyasını açıyoruz
    raster = rioxarray.open_rasterio(tif_file)
    
    # KRİTİK: Veriyi Web Mercator'a (EPSG:3857) çeviriyoruz. 
    # Kaymayı bitiren "on-the-fly" hamlesi budur.
    raster_3857 = raster.rio.reproject("EPSG:3857")
    
    # SHP'yi de aynı sisteme çekiyoruz
    shp = gpd.read_file(shp_file).to_crs("EPSG:3857")

    # 3. HARİTA
    m = leafmap.Map(center=[39, 35], zoom=6, tiles="OpenStreetMap")

    # 4. BOUNDS HESABI (Metre cinsinden ama Folium bunu anlar)
    left, bottom, right, top = raster_3857.rio.bounds()
    # Folium için WGS84 (derece) bounds lazım, o yüzden dereceye geri dönüyoruz sadece sınırlar için
    left_deg, bottom_deg, right_deg, top_deg = raster.rio.bounds()
    bnds = [[bottom_deg, left_deg], [top_deg, right_deg]]

    # 5. RENDER
    # Veriyi resme çeviriyoruz
    vals = raster_3857.values[0] # Band 1
    
    # Maskeleme ve Normalizasyon
    vals = np.where(vals == raster.rio.nodata, np.nan, vals)
    vmin, vmax = np.nanmin(vals), np.nanmax(vals)
    
    # Görüntü yönü kontrolü (Top-down)
    # Web Mercator'da genelde flip gerekir
    vals_plot = np.flipud(vals)

    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    rgba = plt.get_cmap('viridis')(norm(vals_plot))
    
    # Raster Ekle
    ImageOverlay(
        image=rgba,
        bounds=bnds,
        opacity=0.7,
        name="Reprojected Index"
    ).add_to(m)

    # SHP Ekle (Kırmızı)
    # m.add_gdf projeksiyonu otomatik halleder ama biz garantiye alalım
    m.add_gdf(shp, layer_name="SHP Boundaries", style={'color': 'red', 'fillOpacity': 0, 'weight': 1.5})

    # Keskin pikseller
    m.get_root().header.add_child(folium.Element("""
    <style> .leaflet-image-layer { image-rendering: pixelated !important; } </style>
    """))

    m.to_streamlit(height=750)

    # TEŞHİS
    st.write("### Diagnostic")
    st.write(f"Original CRS: {raster.rio.crs}")
    st.write(f"Bounds (Deg): {bnds}")

else:
    st.error("Dosyalar bulunamadı! Lütfen .tif dosyasını push ettiğinden emin ol.")