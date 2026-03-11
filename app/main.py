import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import folium
from folium.raster_layers import ImageOverlay
import os

st.set_page_config(layout="wide")
st.title("Climate Index Map (Aligned Version)")

# --------------------------------------------------
# DOSYA YOLLARI
# --------------------------------------------------

nc_file = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_file = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"


if os.path.exists(nc_file) and os.path.exists(shp_file):

    st.subheader("1️⃣ NetCDF yükleniyor")

    ds = xr.open_dataset(nc_file)

    var_name = [v for v in ds.data_vars if v not in ["spatial_ref", "time_bnds"]][0]

    data = ds[var_name].squeeze()

    # CRS sabitle
    data = data.rio.write_crs("EPSG:4326")

    # --------------------------------------------------
    # LAT YÖNÜ NORMALİZE
    # --------------------------------------------------

    if data.lat[0] < data.lat[-1]:
        data = data.sortby("lat", ascending=False)

    vals = data.values

    # --------------------------------------------------
    # BOUNDS HESABI (MANUEL)
    # --------------------------------------------------

    lat_min = float(data.lat.min())
    lat_max = float(data.lat.max())
    lon_min = float(data.lon.min())
    lon_max = float(data.lon.max())

    res_lat = abs(float(data.lat[1] - data.lat[0]))
    res_lon = abs(float(data.lon[1] - data.lon[0]))

    # pixel-center → pixel-edge düzeltmesi
    lat_min -= res_lat / 2
    lat_max += res_lat / 2
    lon_min -= res_lon / 2
    lon_max += res_lon / 2

    bounds = [[lat_min, lon_min], [lat_max, lon_max]]

    # --------------------------------------------------
    # SHAPEFILE
    # --------------------------------------------------

    shp = gpd.read_file(shp_file)
    shp = shp.to_crs("EPSG:4326")

    # --------------------------------------------------
    # HARİTA
    # --------------------------------------------------

    st.subheader("2️⃣ Harita")

    m = leafmap.Map(center=[39, 35], zoom=6, tiles="OpenStreetMap")

    vmin = float(np.nanmin(vals))
    vmax = float(np.nanmax(vals))

    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    rgba = plt.get_cmap("viridis")(norm(vals))

    ImageOverlay(
        image=rgba,
        bounds=bounds,
        opacity=0.7,
        name="Climate Index"
    ).add_to(m)

    # Türkiye sınırları
    m.add_gdf(
        shp,
        layer_name="Boundaries",
        style={
            "color": "red",
            "fillOpacity": 0,
            "weight": 1.5
        }
    )

    # piksel keskinliği
    m.get_root().header.add_child(folium.Element("""
    <style>
    .leaflet-image-layer {
        image-rendering: pixelated !important;
    }
    </style>
    """))

    m.to_streamlit(height=700)

    # --------------------------------------------------
    # DEBUG PANELİ
    # --------------------------------------------------

    st.subheader("3️⃣ Debug bilgiler")

    col1, col2 = st.columns(2)

    with col1:
        st.write("Min value:", vmin)
        st.write("Max value:", vmax)

        st.write("Lat first 5:", data.lat.values[:5])
        st.write("Lat last 5:", data.lat.values[-5:])

        st.write("Lon first 5:", data.lon.values[:5])
        st.write("Lon last 5:", data.lon.values[-5:])

    with col2:
        st.write("Lat min:", lat_min)
        st.write("Lat max:", lat_max)
        st.write("Lon min:", lon_min)
        st.write("Lon max:", lon_max)

        st.write("Resolution lat:", res_lat)
        st.write("Resolution lon:", res_lon)

        st.write("Array shape:", vals.shape)

else:
    st.error("Dosyalar bulunamadı!")