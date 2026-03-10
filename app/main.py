import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import os
import matplotlib.pyplot as plt
import geopandas as gpd

st.set_page_config(layout="wide")
st.title("Streamlit Cloud - Final Diagnostic")

# Dosya Yolları
test_file = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_file = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm0_2025.shp"

if not os.path.exists(test_file):
    st.error("NC Dosyası bulunamadı!")
else:
    # 1. Veri Hazırlama
    ds = xr.open_dataset(test_file)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    data.rio.write_crs("EPSG:4326", inplace=True)

    # 2. Interaktif Harita (Leafmap/Folium)
    st.subheader("1. Interaktif Harita (Simple Overlay)")
    # Tiles=None diyerek OSM'i kapatıyoruz
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)
    
    # SHP Ekle (Türkiye Sınırı)
    if os.path.exists(shp_file):
        shp_gdf = gpd.read_file(shp_file)
        m.add_gdf(shp_gdf, layer_name="Türkiye", style={'color': 'black', 'fillOpacity': 0})
    
    # add_raster yerine add_data_array deniyoruz (Daha hafif bir render)
    try:
        m.add_data_array(data, label=var_name, palette="viridis", layer_name="Raster Veri")
    except Exception as e:
        st.warning(f"Raster çizim hatası: {e}")

    m.to_streamlit(height=500)

    # 3. Statik Plot (Matplotlib - Hata Payı Sıfır)
    st.subheader("2. Statik Doğrulama (Matplotlib)")
    fig, ax = plt.subplots(figsize=(10, 5))
    data.plot(ax=ax, cmap="viridis")
    if os.path.exists(shp_file):
        shp_gdf.boundary.plot(ax=ax, color="black", linewidth=1)
    st.pyplot(fig)

    # 4. Veri Özeti
    st.write(f"Veri Boyutu: {data.shape}")