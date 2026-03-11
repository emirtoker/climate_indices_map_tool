import streamlit as st
import xarray as xr
import geopandas as gpd
import leafmap.foliumap as leafmap # Streamlit için folium tabanlı olanı kullanıyoruz
import os
import numpy as np

st.set_page_config(layout="wide")
st.title("Streamlit Online CRS Test")

# 1. YOLLAR (Online için relative path kullanıyoruz)
# data klasörünün app ile aynı seviyede veya root'ta olduğunu varsayıyorum
nc_file = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_file = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_file) and os.path.exists(shp_file):
    # 2. VERİYİ OKU VE CRS MÜHÜRLE
    ds = xr.open_dataset(nc_file)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    
    # Notebook'ta hayat kurtaran mühür
    data.rio.write_crs("EPSG:4326", inplace=True)
    
    # SHP Oku
    shp = gpd.read_file(shp_file)

    # 3. HARİTA (Streamlit uyumlu motor)
    m = leafmap.Map(center=[39, 35], zoom=6, tiles="OpenStreetMap")

    # 4. RASTER EKLE
    # NOT: Online'da add_raster bazen 'local-tileserver' olmadığı için beyaz gelebilir.
    # Eğer beyaz gelirse bana söyle, ImageOverlay'e bu CRS ile döneceğiz.
    try:
        m.add_raster(
            data, 
            layer_name="Index: " + var_name, 
            palette="viridis", 
            opacity=0.7
        )
    except Exception as e:
        st.error(f"Raster yüklenirken hata: {e}")

    # 5. SHP EKLE
    m.add_gdf(
        shp, 
        layer_name="Boundaries", 
        style={'color': 'red', 'fillOpacity': 0, 'weight': 1.5}
    )

    # 6. STREAMLIT'E BAS (En kritik fark bu)
    m.to_streamlit(height=700)

else:
    st.error("Dosyalar online sunucuda bulunamadı!")
    st.write(f"NC: {os.path.exists(nc_file)}, SHP: {os.path.exists(shp_file)}")