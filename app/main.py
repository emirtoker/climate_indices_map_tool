import streamlit as st
import leafmap.foliumap as leafmap
import rioxarray
import geopandas as gpd
import os
import numpy as np
import matplotlib.pyplot as plt
from folium.raster_layers import ImageOverlay
import folium

st.set_page_config(layout="wide")
st.title("Final Fix: Metric to Degree Alignment")

# 1. DOSYA YOLLARI
tif_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.tif"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(tif_path) and os.path.exists(shp_path):
    # 2. VERİ OKUMA
    raster = rioxarray.open_rasterio(tif_path)
    
    # SHP'yi her zaman WGS84 (Derece) olarak okuyoruz, harita motoru bunu sever
    shp = gpd.read_file(shp_path).to_crs("EPSG:4326")

    # 3. BOUNDS HESABI (Kritik Nokta!)
    # Tif dosyan metre (3857) olduğu için, Folium'a vereceğimiz sınırları 
    # tekrar dereceye (4326) çevirmemiz lazım ki harita nerede olduğunu anlasın.
    raster_4326 = raster.rio.reproject("EPSG:4326")
    left, bottom, right, top = raster_4326.rio.bounds()
    bnds = [[bottom, left], [top, right]]

    # 4. HARİTA
    m = leafmap.Map(center=[39, 35], zoom=6, tiles="OpenStreetMap")

    # 5. RENDER (Görsel Hazırlama)
    # Veriyi al (Band 1)
    vals = raster.values[0]
    
    # NoData (nan) temizliği
    nodata = raster.rio.nodata
    vals_clean = np.where(vals == nodata, np.nan, vals)
    
    # Renk aralığı
    vmin, vmax = np.nanmin(vals_clean), np.nanmax(vals_clean)    

    # YÖN KONTROLÜ: Tif'ten gelen veri genelde terstir, harita için düzeltiyoruz
    # Eğer harita ters çıkarsa bunu kaldırırız
    vals_plot = vals_clean # Veriyi olduğu gibi alıyoruz
    
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    rgba = plt.get_cmap('viridis')(norm(vals_plot))
    
    # RASTER EKLE (Derece cinsinden bounds ile)
    ImageOverlay(
        image=rgba,
        bounds=bnds,
        opacity=0.7,
        name="Summer Days (TIF)"
    ).add_to(m)

    # SHP EKLE
    m.add_gdf(shp, layer_name="İl Sınırları", style={'color': 'red', 'fillOpacity': 0, 'weight': 1.5})

    m.to_streamlit(height=750)

    # TEŞHİS (Artık burada mantıklı derece rakamları görmelisin: 35-45 arası)
    st.write("### Diagnostic")
    st.write(f"Corrected Degree Bounds: {bnds}")
    st.write(f"Min/Max Value: {vmin:.2f} / {vmax:.2f}")

else:
    st.error("Dosyalar eksik!")