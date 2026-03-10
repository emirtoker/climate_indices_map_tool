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
st.title("Final Solution: Proj-Aware Interactive Map")

# 1. DOSYA YOLLARI
nc_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_path) and os.path.exists(shp_path):
    # 2. VERİ OKUMA
    ds = xr.open_dataset(nc_path)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: data = data.mean('time')
    
    # SHP Yükle ve Raster ile aynı projeksiyona getir
    shp = gpd.read_file(shp_path).to_crs("EPSG:4326")

    # 3. HARİTA (Arka planı kapattım, sadece senin verin)
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)

    # 4. KRİTİK: RIOXARRAY İLE GERÇEK SINIRLARI AL
    # Notebook'ta Cartopy'nin yaptığı 'extent' hesabını rioxarray ile alıyoruz
    # Bu metod manuel 'res/2' hesabından çok daha güvenlidir.
    try:
        left, bottom, right, top = data.rio.bounds()
        bnds = [[bottom, left], [top, right]]
    except:
        # Rioxarray yoksa veya hata verirse ham koordinatlardan al
        bnds = [[float(data.lat.min()), float(data.lon.min())], 
                [float(data.lat.max()), float(data.lon.max())]]

    # 5. RENDER (Renklendirme)
    vmin, vmax = float(data.min()), float(data.max())
    vals = data.values
    
    # NetCDF yön kontrolü (Ekseni düzelt)
    if data.lat[0] < data.lat[-1]:
        vals = np.flipud(vals)

    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    rgba = plt.get_cmap('viridis')(norm(vals))
    
    # 6. KATMANLARI BİNDİR
    # Önce Raster (Altta)
    ImageOverlay(
        image=rgba,
        bounds=bnds,
        opacity=0.8,
        name="Climate Index"
    ).add_to(m)
    
    # Sonra SHP (Üstte - Kırmızı)
    m.add_gdf(shp, layer_name="Administrative Boundaries", style={'color': 'red', 'fillOpacity': 0, 'weight': 1.5})

    # Keskin pikseller için CSS mühürü
    m.get_root().header.add_child(folium.Element("""
    <style> .leaflet-image-layer { image-rendering: pixelated !important; } </style>
    """))

    m.to_streamlit(height=800)

    st.write("### Diagnostic")
    st.write(f"Bounds Used: {bnds}")
    st.write(f"Data CRS: {data.rio.crs if hasattr(data, 'rio') else 'Not Set'}")

else:
    st.error("Dosyalar bulunamadı!")