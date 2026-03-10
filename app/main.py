import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import geopandas as gpd
import os
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide", page_title="Deep Diagnostic")
st.title("Deep Diagnostic: Why is it White?")

nc_path = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"
shp_path = "data/shapefiles/tur_adm_2025_ab_shp/tur_admbnda_adm1_2025.shp"

if os.path.exists(nc_path):
    # 1. VERİ KONTROLÜ
    ds = xr.open_dataset(nc_path)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    data = ds[var_name].squeeze()
    if 'time' in data.dims: data = data.mean('time')

    # Ekrana Veri Özetini Bas (Değerler gerçekten orada mı?)
    st.write("### Data Integrity Check")
    col1, col2, col3 = st.columns(3)
    col1.metric("Min Value", f"{float(data.min()):.2f}")
    col2.metric("Max Value", f"{float(data.max()):.2f}")
    col3.metric("NaN Count", f"{int(data.isnull().sum())}")

    # 2. PROJEKSİYON KONTROLÜ
    st.write("### Coordinate Reference System (CRS)")
    st.code(f"Native CRS: {data.rio.crs}")
    st.write(f"Spatial Ref Attrs: {ds.spatial_ref.attrs if 'spatial_ref' in ds else 'No spatial_ref found'}")

    # 3. HARİTA TESTİ (Düşük Çözünürlüklü Önizleme)
    st.write("### Static vs Interactive Comparison")
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("Statik Plot (Matplotlib - Asla yanılmaz)")
        fig, ax = plt.subplots()
        data.plot(ax=ax, cmap='viridis')
        st.pyplot(fig)
    
    with c2:
        st.write("Interaktif Plot (Leafmap - Sorunlu bölge)")
        m = leafmap.Map(center=[39, 35], zoom=6)
        # Burada en hafif yöntemi deniyoruz: ImageOverlay ama manuel normalize ile
        # Eğer bu da beyaz gelirse tarayıcı render edemiyor demektir.
        
        vmin, vmax = float(data.min()), float(data.max())
        norm = (data.values - vmin) / (vmax - vmin)
        norm = np.clip(norm, 0, 1)
        
        # ImageOverlay sınırlarını basitleştirilmiş bir şekilde veriyoruz
        from folium.raster_layers import ImageOverlay
        rgba = plt.get_cmap('viridis')(norm)
        rgba = np.flipud(rgba)
        
        # Sınırları manuel notebook tarzı yazalım
        bnds = [[float(data.lat.min()), float(data.lon.min())], 
                [float(data.lat.max()), float(data.lon.max())]]
        
        ImageOverlay(image=rgba, bounds=bnds, opacity=0.7).add_to(m)
        m.to_streamlit(height=400)

    # 4. SİSTEM BİLGİSİ (Sunucu Kapasitesi)
    st.write("### Environment Info")
    import sys
    st.write(f"Python Version: {sys.version}")
    try:
        import local_tileserver
        st.write(f"Local TileServer Version: {local_tileserver.__version__}")
    except:
        st.write("❌ Local TileServer NOT INSTALLED (This is why add_raster fails online)")

else:
    st.error("Data folder not found!")