import streamlit as st
import xarray as xr
import geopandas as gpd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os
import numpy as np

st.set_page_config(layout="wide")
st.title("Cartopy-Native Projection Alignment")

# 1. DOSYA YOLLARI
nc_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_path) and os.path.exists(shp_path):
    # 2. VERİ OKUMA
    ds = xr.open_dataset(nc_path)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: data = data.mean('time')
    
    # SHP Yükle
    shp = gpd.read_file(shp_path)

    # 3. PLOT AYARLARI (Sidebar)
    cmap_choice = st.sidebar.selectbox("Renk Paleti", ["viridis", "Spectral_r", "RdYlBu_r", "magma"])
    
    # 4. CARTOPY MÜHENDİSLİĞİ
    # Projeksiyonu tanımlıyoruz (Senin veriler WGS84 olduğu için PlateCarree)
    projection = ccrs.PlateCarree()
    
    fig, ax = plt.subplots(figsize=(12, 8), subplot_kw={'projection': projection}, dpi=150)
    
    # Arka plan ve denizleri ekle (Opsiyonel)
    ax.add_feature(cfeature.OCEAN, facecolor='aliceblue')
    ax.add_feature(cfeature.LAND, facecolor='white')

    # --- KRİTİK KATMAN 1: RASTER ---
    # pcolormesh kullanarak her pikseli kendi koordinatına çiviliyoruz
    # Kayma (offset) ihtimalini kökten bitiren budur.
    im = data.plot(
        ax=ax, 
        transform=projection, 
        cmap=cmap_choice, 
        add_colorbar=True,
        cbar_kwargs={'label': var_name, 'pad': 0.02, 'shrink': 0.6},
        zorder=1
    )

    # --- KRİTİK KATMAN 2: SHP ---
    # SHP'yi aynı projeksiyonla üzerine çiziyoruz
    shp.plot(
        ax=ax, 
        transform=projection, 
        edgecolor='red', 
        facecolor='none', 
        linewidth=0.5, 
        zorder=2
    )

    # Türkiye Odaklı Sınırlar (Extent)
    ax.set_extent([25, 45, 35, 43], crs=projection)
    
    # Gridlines (Opsiyonel)
    ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False, alpha=0.3)

    st.pyplot(fig)

    # TEŞHİS
    st.write("### Diagnostic Info")
    st.write(f"Raster Data Range: {float(data.min()):.2f} to {float(data.max()):.2f}")
    st.write(f"SHP CRS: {shp.crs}")

else:
    st.error("Dosyalar bulunamadı! Lütfen data klasörünü kontrol et.")