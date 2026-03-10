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
st.title("Notebook-Style Interactive Alignment")

nc_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_path) and os.path.exists(shp_path):
    # 1. VERİ OKUMA
    ds = xr.open_dataset(nc_path)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: data = data.mean('time')
    
    # SHP Yükle
    shp = gpd.read_file(shp_path).to_crs("EPSG:4326")

    # 2. HARİTA (Arka plan yok, sadece senin sınırların)
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)

    # 3. MILIMETRIK BOUNDS (NetCDF Metadata'dan direkt çekiyoruz)
    # Rioxarray'in bize verdiği gerçek coğrafi sınırlar
    west, south, east, north = data.rio.bounds()
    bnds = [[south, west], [north, east]]

    # 4. RENDER (Notebook'taki görselin aynısını üretiyoruz)
    # Notebook'ta gördüğün o kusursuz renk dizilimini matrise döküyoruz
    vmin, vmax = float(data.min()), float(data.max())
    
    # Renklendirme için Matplotlib motorunu kullanıyoruz (En garanti yol)
    cmap = plt.get_cmap('viridis')
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    
    # ÖNEMLİ: Notebook'ta 'imshow' veya 'pcolormesh' veriyi nasıl görüyorsa öyle alıyoruz
    # Hiçbir flip (takla) atmadan, ham haliyle.
    rgba_data = cmap(norm(data.values))
    
    # Folium resmi üstten aşağı (top-down) okur. 
    # Eğer harita ters dönüyorsa, NetCDF'in y ekseni (lat) azalan sıradadır.
    # Bu sefer manuel flip yerine verinin lat dizilimine bakıp karar veriyoruz.
    if data.lat[0] > data.lat[-1]:
        # Eğer enlemler yukarıdan aşağı diziliyse (Kuzeyden Güneye), 
        # ImageOverlay için bu dizilim doğrudur, flip yapma.
        final_rgba = rgba_data
    else:
        # Eğer enlemler aşağıdan yukarı diziliyse, flip yap.
        final_rgba = np.flipud(rgba_data)

    # 5. KATMANLARI EKLE
    # Raster
    ImageOverlay(
        image=final_rgba,
        bounds=bnds,
        opacity=0.8,
        name="Aligned Raster"
    ).add_to(m)

    # SHP (Raster'ın tam üstüne kırmızı çizgiler)
    m.add_gdf(shp, layer_name="SHP Boundaries", style={'color': 'red', 'fillOpacity': 0, 'weight': 1.5})

    m.to_streamlit(height=800)

    # TEŞHİS
    st.write("### Diagnostic")
    st.write(f"Lat[0]: {data.lat[0].values:.4f}, Lat[-1]: {data.lat[-1].values:.4f}")
    st.write(f"Bounds: {bnds}")

else:
    st.error("Dosyalar eksik!")