import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import geopandas as gpd
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import branca.colormap as cm
import folium
from folium.raster_layers import ImageOverlay

st.set_page_config(layout="wide", page_title="Online Diagnostic Test")
st.title("Diagnostic Interactive Test (Online Mode)")

# 1. DOSYA YOLLARI
nc_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

nc_exists = os.path.exists(nc_path)
shp_exists = os.path.exists(shp_path)

if nc_exists and shp_exists:
    # 2. VERİ YÜKLEME
    ds = xr.open_dataset(nc_path)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: 
        data = data.mean('time')
    
    lon_n = 'lon' if 'lon' in data.coords else ('x' if 'x' in data.coords else 'longitude')
    lat_n = 'lat' if 'lat' in data.coords else ('y' if 'y' in data.coords else 'latitude')
    
    shp = gpd.read_file(shp_path)
    
    # 3. SIDEBAR
    st.sidebar.header("Map Settings")
    cmap_choice = st.sidebar.selectbox("Color Palette", ["viridis", "Spectral_r", "RdYlBu_r", "magma", "plasma"])
    alpha_val = st.sidebar.slider("Opacity", 0.0, 1.0, 0.7)
    
    # 4. HARİTA MOTORU
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)
    
    m.get_root().header.add_child(folium.Element("""
    <style> .leaflet-image-layer { image-rendering: pixelated !important; } </style>
    """))

    # SHP Katmanı (Sınırlar) - zindex için sonradan ekleme mantığı
    m.add_gdf(shp, layer_name="Türkiye Boundaries", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.0})

    # 5. RASTER TO IMAGEOVERLAY (MİLİMETRİK HESAP)
    # [Image of pixel alignment in GIS data comparing center and corner coordinates]
    
    # Koordinat vektörlerini al
    lons = data[lon_n].values
    lats = data[lat_n].values
    
    # Çözünürlük hesabı (Piksel merkezleri arası mesafe)
    d_lon = (lons[-1] - lons[0]) / (len(lons) - 1)
    d_lat = (lats[-1] - lats[0]) / (len(lats) - 1)
    
    # KÖŞE SINIRLARI (Merkezden dışa yarım piksel esnetme)
    # Folium bizden [[min_lat, min_lon], [max_lat, max_lon]] bekler
    # res_y veya res_x negatif olsa bile abs() ile yönü koruyoruz
    west = lons.min() - abs(d_lon) / 2
    east = lons.max() + abs(d_lon) / 2
    south = lats.min() - abs(d_lat) / 2
    north = lats.max() + abs(d_lat) / 2
    
    bnds = [[south, west], [north, east]]
    
    # Render için Normalizasyon
    vmin, vmax = float(data.min()), float(data.max())
    vals = data.values
    
    # Veri dizilimi kontrolü: Eğer enlemler (lat) yukarıdan aşağıya (descending) diziliyse flip gerekir
    # NetCDF standartlarında genelde lat[0] > lat[-1] olur.
    if lats[0] > lats[-1]:
        plot_vals = vals
    else:
        plot_vals = np.flipud(vals)
        
    norm = (plot_vals - vmin) / (vmax - vmin)
    norm = np.clip(norm, 0, 1)
    
    cmap = plt.get_cmap(cmap_choice)
    rgba = cmap(norm)
    
    # Katmanı ekle
    ImageOverlay(image=rgba, bounds=bnds, opacity=alpha_val, name="Climate Index Layer").add_to(m)

    # 6. COLORBAR
    colors = [mpl.colors.rgb2hex(cmap(i)) for i in np.linspace(0, 1, 256)]
    cmap_obj = cm.LinearColormap(colors=colors, vmin=vmin, vmax=vmax, caption=f"{var_name} Index")
    m.add_child(cmap_obj)

    m.to_streamlit(height=800)
    
    st.success(f"Successfully rendered {var_name}")
    st.write(f"Calculated Bounds (Edge-to-Edge): {bnds}")

else:
    st.error("FILES NOT FOUND!")