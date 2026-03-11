import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import os
from folium.raster_layers import ImageOverlay

st.set_page_config(layout="wide")
st.title("NetCDF Climate Map")

nc_file = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_file = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_file) and os.path.exists(shp_file):

    ds = xr.open_dataset(nc_file)

    var = [v for v in ds.data_vars if v not in ["spatial_ref","time_bnds"]][0]

    data = ds[var].squeeze()

    lat = data.lat.values
    lon = data.lon.values
    vals = data.values

    # resolution
    lat_res = abs(lat[1] - lat[0])
    lon_res = abs(lon[1] - lon[0])

    # pixel center -> pixel edge correction
    lat_min = lat.min() - lat_res/2
    lat_max = lat.max() + lat_res/2
    lon_min = lon.min() - lon_res/2
    lon_max = lon.max() + lon_res/2

    bounds = [[lat_min, lon_min], [lat_max, lon_max]]

    # orientation kontrolü
    if lat[0] < lat[-1]:
        vals = np.flipud(vals)

    # renk
    vmin = float(np.nanmin(vals))
    vmax = float(np.nanmax(vals))

    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    rgba = plt.get_cmap("viridis")(norm(vals))

    # harita
    m = leafmap.Map(center=[39,35], zoom=6)

    ImageOverlay(
        image=rgba,
        bounds=bounds,
        opacity=0.7,
        name="Climate"
    ).add_to(m)

    # shp
    shp = gpd.read_file(shp_file).to_crs("EPSG:4326")

    m.add_gdf(
        shp,
        layer_name="Boundaries",
        style={"color":"red","fillOpacity":0,"weight":1.5}
    )

    m.to_streamlit(height=700)

    st.subheader("Debug")

    st.write("Lat min:", lat.min())
    st.write("Lat max:", lat.max())
    st.write("Lon min:", lon.min())
    st.write("Lon max:", lon.max())

    st.write("Resolution lat:", lat_res)
    st.write("Resolution lon:", lon_res)

    st.write("Bounds used:", bounds)

    st.write("Array shape:", vals.shape)

else:
    st.error("Files not found")