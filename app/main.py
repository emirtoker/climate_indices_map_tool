import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import geopandas as gpd
import rioxarray
import os

st.set_page_config(layout="wide")
st.title("NetCDF Map Test (Direct Xarray)")

nc_file = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_file = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_file) and os.path.exists(shp_file):

    st.subheader("NetCDF yükleniyor")

    ds = xr.open_dataset(nc_file)

    var_name = [v for v in ds.data_vars if v not in ["spatial_ref","time_bnds"]][0]

    data = ds[var_name].squeeze()

    # CRS yaz
    data = data.rio.write_crs("EPSG:4326")

    st.write("Variable:", var_name)
    st.write(data)

    shp = gpd.read_file(shp_file).to_crs("EPSG:4326")

    # Harita
    m = leafmap.Map(center=[39,35], zoom=6, tiles="OpenStreetMap")

    # NetCDF raster ekle
    m.add_xarray(
        data,
        layer_name="Climate Index",
        colormap="viridis"
    )

    # Türkiye sınırları
    m.add_gdf(
        shp,
        layer_name="Boundaries",
        style={"color":"red","fillOpacity":0,"weight":1.5}
    )

    m.to_streamlit(height=700)

    st.subheader("Debug")

    st.write("Lat min:", float(data.lat.min()))
    st.write("Lat max:", float(data.lat.max()))
    st.write("Lon min:", float(data.lon.min()))
    st.write("Lon max:", float(data.lon.max()))
    st.write("Shape:", data.shape)

else:
    st.error("Dosyalar bulunamadı")