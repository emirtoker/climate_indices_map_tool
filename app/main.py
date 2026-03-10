import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import os
import matplotlib.pyplot as plt
import numpy as np
from folium.raster_layers import ImageOverlay

st.set_page_config(layout="wide")
st.title("Streamlit Cloud - Interactive Success")

test_file = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"

if os.path.exists(test_file):
    # 1. Veriyi Oku ve Hazırla
    ds = xr.open_dataset(test_file)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    
    # Koordinat sınırlarını al (ImageOverlay için şart)
    bounds = [[float(data.y.min()), float(data.x.min())], [float(data.y.max()), float(data.x.max())]]

    # 2. Veriyi Renkli Bir Resme (RGBA) Dönüştür
    # Bu adım GDAL bağımlılığını baypas eder
    norm_data = (data - data.min()) / (data.max() - data.min()) # 0-1 arası normalize
    cmap = plt.get_cmap('viridis')
    rgba_data = cmap(norm_data) # Renk paletini uygula
    
    # 3. İnteraktif Harita
    m = leafmap.Map(center=[39, 35], zoom=6, tiles="OpenStreetMap")
    
    # ImageOverlay kullanarak veriyi haritaya "çakıyoruz"
    ImageOverlay(
        image=rgba_data,
        bounds=bounds,
        opacity=0.7,
        name="Raster Layer (Stable Mode)"
    ).add_to(m)

    m.to_streamlit(height=600)
    
    st.success("İnteraktif haritada ImageOverlay kullanıldı. Renkler gelmiş olmalı!")