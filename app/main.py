import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import os
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from folium.raster_layers import ImageOverlay
import branca.colormap as cm

st.set_page_config(layout="wide")
st.title("Final Multi-Color Logic Test")

# Test Dosyası
test_file = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"

if os.path.exists(test_file):
    # 1. Veri Okuma (Hiçbir manipülasyon yok)
    ds = xr.open_dataset(test_file)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: data = data.mean('time')

    # 2. Görsel Konfigürasyon (Senin map_engine'deki Multi-Color ayarların)
    vmin_val = 0.0
    vmax_val = 200.0
    cmap_name = "viridis"
    alpha = 0.8

    # 3. Manuel Render Hazırlığı (ImageOverlay için)
    # Koordinat isimlerini yakala
    lat_n = 'lat' if 'lat' in data.coords else ('y' if 'y' in data.coords else None)
    lon_n = 'lon' if 'lon' in data.coords else ('x' if 'x' in data.coords else None)

    if lat_n and lon_n:
        # Değerleri vmin/vmax arasına sıkıştır ve normalize et
        vals = data.values
        norm = (vals - vmin_val) / (vmax_val - vmin_val)
        norm = np.clip(norm, 0, 1)

        # Colormap uygula
        cmap = plt.get_cmap(cmap_name)
        rgba = cmap(norm)
        
        # Kuzey-Güney düzeltmesi (Flip)
        rgba = np.flipud(rgba)

        # Harita Sınırları
        bnds = [[float(data[lat_n].min()), float(data[lon_n].min())], 
                [float(data[lat_n].max()), float(data[lon_n].max())]]

        # 4. Harita Kurulumu
        m = leafmap.Map(center=[39, 35], zoom=6, tiles=None)
        
        # ImageOverlay Ekle
        ImageOverlay(
            image=rgba,
            bounds=bnds,
            opacity=alpha,
            name=f"Test: {var_name}"
        ).add_to(m)

        # 5. Colorbar Ekle (Branca - Senin orijinal projedeki gibi)
        colors = [mpl.colors.rgb2hex(cmap(i)) for i in np.linspace(0, 1, 256)]
        caption = f"{var_name} (Test Unit)"
        cmap_obj = cm.LinearColormap(colors=colors, vmin=vmin_val, vmax=vmax_val, caption=caption)
        m.add_child(cmap_obj.to_step(index=np.linspace(vmin_val, vmax_val, 6)))

        m.to_streamlit(height=700)
        
        st.success(f"Multi-color logic applied for {var_name}")
        st.write(f"Range: {vmin_val} - {vmax_val} | Palette: {cmap_name}")
    else:
        st.error("Coords not found!")
else:
    st.error("File not found!")