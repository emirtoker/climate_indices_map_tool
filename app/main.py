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
st.title("The Final Showdown: GeoTIFF vs NetCDF Alignment")

# 1. YOLLAR
tif_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.tif"
nc_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

# Ortak Render Fonksiyonu (Hata payını sıfırlamak için)
def get_layer_data(file_path):
    raster = rioxarray.open_rasterio(file_path)
    # CRS mühürü yoksa bas (özellikle NC için)
    if raster.rio.crs is None:
        raster.rio.write_crs("EPSG:4326", inplace=True)
    
    # Sınırları derece cinsinden al
    raster_4326 = raster.rio.reproject("EPSG:4326")
    left, bottom, right, top = raster_4326.rio.bounds()
    bounds = [[bottom, left], [top, right]]
    
    # Veriyi temizle
    vals = raster.values[0]
    nodata = raster.rio.nodata
    vals_clean = np.where(vals == nodata, np.nan, vals)
    
    # Tif/NC farkına göre flip gerekebilir, şimdilik ikisini de düz bırakıyoruz
    return vals_clean, bounds, np.nanmin(vals_clean), np.nanmax(vals_clean)

if all(os.path.exists(p) for p in [tif_path, nc_path, shp_path]):
    shp = gpd.read_file(shp_path).to_crs("EPSG:4326")
    
    # --- HARİTA 1: GeoTIFF (Şampiyon) ---
    st.subheader("1. GeoTIFF Katmanı (Referans)")
    m1 = leafmap.Map(center=[39, 35], zoom=6, tiles="OpenStreetMap")
    vals_tif, bnds_tif, vmin_tif, vmax_tif = get_layer_data(tif_path)
    
    rgba_tif = plt.get_cmap('viridis')(plt.Normalize(vmin_tif, vmax_tif)(vals_tif))
    ImageOverlay(image=rgba_tif, bounds=bnds_tif, opacity=0.7, name="TIFF").add_to(m1)
    m1.add_gdf(shp, style={'color': 'red', 'weight': 1.5})
    m1.to_streamlit(height=500, key="map_tif")

    st.divider()

    # --- HARİTA 2: NetCDF (Aday) ---
    st.subheader("2. NetCDF Katmanı (Test)")
    m2 = leafmap.Map(center=[39, 35], zoom=6, tiles="OpenStreetMap")
    vals_nc, bnds_nc, vmin_nc, vmax_nc = get_layer_data(nc_path)
    
    # NOT: NC verisi genelde TIF'e göre terstir, eğer ters gelirse flipud ekleriz
    rgba_nc = plt.get_cmap('plasma')(plt.Normalize(vmin_nc, vmax_nc)(vals_nc))
    ImageOverlay(image=rgba_nc, bounds=bnds_nc, opacity=0.7, name="NetCDF").add_to(m2)
    m2.add_gdf(shp, style={'color': 'cyan', 'weight': 1.5})
    m2.to_streamlit(height=500, key="map_nc")

    # Kıyaslama Bilgisi
    st.write("### Karşılaştırma Notları")
    col1, col2 = st.columns(2)
    col1.write(f"TIFF Bounds: {bnds_tif}")
    col2.write(f"NetCDF Bounds: {bnds_nc}")

else:
    st.error("Dosyalar eksik!")