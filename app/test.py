import matplotlib
matplotlib.use('Agg') 

import streamlit as st
import rioxarray
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import leafmap.foliumap as leafmap
from folium.raster_layers import ImageOverlay
import os
import time

# 1. PATH
tif_path = "/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/Script/Python/climate_indices_map_tool/data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.tif"

# 2. DATA LOADING
@st.cache_data
def load_and_clean_data(path):
    raster = rioxarray.open_rasterio(path)
    data = raster.values[0]
    cleaned = np.where(data == raster.rio.nodata, np.nan, data)
    # Bounds for Folium
    data_4326 = raster.rio.reproject("EPSG:4326")
    return cleaned, data_4326.rio.bounds()

data_clean, bnds_raw = load_and_clean_data(tif_path)
left, bottom, right, top = bnds_raw
bnds = [[bottom, left], [top, right]]

# 3. SIDEBAR
selected_color = st.sidebar.color_picker("Color Picker", "#FF0000")
opacity = st.sidebar.slider("Opacity", 0.0, 1.0, 0.7)

# 4. RGBA ENGINE (FORCED UINT8)
def get_folium_ready_rgba(data, hex_color):
    mask = ~np.isnan(data)
    # Create float array first (0.0 - 1.0)
    rgba_float = np.zeros((*data.shape, 4))
    rgba_float[mask] = mpl.colors.to_rgba(hex_color)
    
    # CRITICAL: Convert to uint8 (0-255) for browser compatibility
    # Folium's ImageOverlay often fails with float arrays on re-renders
    rgba_uint8 = (rgba_float * 255).astype(np.uint8)
    return rgba_uint8

rgba_image = get_folium_ready_rgba(data_clean, selected_color)

# 5. RENDER INTERACTIVE MAP
st.write(f"Current Hex: {selected_color}")

# Force refresh with a unique key on every rerun
m_key = f"map_render_{selected_color}_{time.time()}"
m = leafmap.Map(center=[39, 35], zoom=6)

ImageOverlay(
    image=rgba_image, # This is now uint8
    bounds=bnds,
    opacity=opacity,
    name="Climate Layer",
    zindex=10
).add_to(m)

m.to_streamlit(height=600, key=m_key)

# 6. STATIC CHECK
fig, ax = plt.subplots(figsize=(10, 2))
ax.imshow(rgba_image)
ax.set_title("RGBA Matrix Check (uint8)")
ax.set_axis_off()
st.pyplot(fig)