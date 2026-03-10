import streamlit as st
import leafmap.foliumap as leafmap
import xarray as xr
import os

st.set_page_config(layout="wide")
st.title("Streamlit Cloud Environment Test")

# Senin tree yapındaki en güvenli path'i verdim
test_file = "data/indices/historical/climatology/1km/CHELSA/CHELSA_TR_yearly_1995_2014_SU_summer_days.nc"

if not os.path.exists(test_file):
    st.error(f"DOSYA YOK: {test_file}")
else:
    st.success("DOSYA BULUNDU")
    
    # Veriyi aç ve ham halini gör
    ds = xr.open_dataset(test_file)
    var_name = [v for v in ds.data_vars if v not in ['spatial_ref', 'time_bnds']][0]
    
    # KRİTİK: Squeeze ve CRS mühürleme (Lokal-Server farkını sıfırlamak için)
    data = ds[var_name].squeeze()
    data.rio.write_crs("EPSG:4326", inplace=True)
    
    # Ekrana değerleri yazdır (Burası doluysa dosya sağlamdır)
    st.write(f"Değişken: {var_name}")
    st.write(f"Değer Aralığı: {float(data.min())} - {float(data.max())}")
    
    # Harita Testi
    m = leafmap.Map(center=[39, 35], zoom=6)
    
    # En basit haliyle raster ekle
    m.add_raster(data, layer_name="Test Layer", palette="viridis", opacity=1.0)
    
    m.to_streamlit(height=600)
    
    # Eğer harita hala boşsa, leafmap'in sunucu tarafındaki çizim motoru patlıyor demektir.