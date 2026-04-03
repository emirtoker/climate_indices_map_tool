import streamlit as st
import leafmap.foliumap as leafmap
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import branca.colormap as cm
import folium
from folium.raster_layers import ImageOverlay 
from PIL import Image
import io
import base64

# --- AŞAMA 1: DISK OKUMA CACHE (En Ağır İşlem) ---
@st.cache_data(show_spinner=False)
def load_raw_data(file_name):
    """Veriyi diskten sadece 1 kere okur ve RAM'de tutar."""
    from core.data_loader import load_index_data
    data, _, _ = load_index_data(file_name)
    return data

# --- AŞAMA 2: PNG ENCODE CACHE (CPU Optimizasyonu) ---
@st.cache_data(show_spinner=False)
def rgba_to_png_base64(rgba_uint8):
    img = Image.fromarray(rgba_uint8)
    buf = io.BytesIO()
    # optimize=True kaldırıldı; CPU yükünü azaltmak için hızlı kayıt tercih edildi
    img.save(buf, format="PNG") 
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

# --- AŞAMA 3: RENKLENDİRME CACHE (RAM İşlemi) ---
@st.cache_data(show_spinner=False)
def get_cached_rgba(file_name, vmin, vmax, cmap_input, mode, thresh=None, color_below=None, color_above=None, no_b=False, no_a=False):
    # DİKKAT: Veriyi diskten değil, RAM'deki cache'den alıyoruz
    data = load_raw_data(file_name)
    
    vals = data.values
    mask = ~np.isnan(vals)
    rgba = np.zeros((*vals.shape, 4), dtype=np.float32)

    if mode == "Threshold":
        t = thresh
        if not no_b: 
            idx = mask & (vals < t); rgba[idx, :3] = mpl.colors.to_rgba(color_below)[:3]; rgba[idx, 3] = 1.0
        if not no_a: 
            idx = mask & (vals > t); rgba[idx, :3] = mpl.colors.to_rgba(color_above)[:3]; rgba[idx, 3] = 1.0
    else:
        valid = mask & (vals >= vmin) & (vals <= vmax)
        if isinstance(cmap_input, str) and cmap_input.startswith('#'):
            rgba[valid, :3] = mpl.colors.to_rgba(cmap_input)[:3]
        else:
            norm = plt.Normalize(vmin=vmin, vmax=vmax)
            rgba[valid, :3] = plt.get_cmap(cmap_input)(norm(vals[valid]))[:, :3]
        rgba[valid, 3] = 1.0 
    
    left, bottom, right, top = data.rio.transform_bounds("EPSG:4326")
    return (rgba * 255).astype(np.uint8), [[bottom, left], [top, right]]

# ... (get_synthesis_rgba fonksiyonu da load_raw_data kullanacak şekilde güncellenmeli)

def create_interactive_map(shp, one_bundle, multi_bundle, units_dict, available_dict):
    m = leafmap.Map(center=st.session_state.get('map_center', [38.9, 35.5]), zoom=st.session_state.get('map_zoom', 5), tiles=None)

    # ANA CSS - LOOP DIŞINDA
    m.get_root().header.add_child(folium.Element("""
    <style>
    .leaflet-image-layer { image-rendering: pixelated !important; }
    .legend { font-size: 16px !important; flex-direction: column-reverse !important; }
    </style>
    """))
    
    if shp is not None:
        temp_shp = shp[['ADM1_TR', 'geometry']].copy(); temp_shp.columns = ['TR', 'geometry']
        m.add_gdf(temp_shp, layer_name="Türkiye Provinces", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.0}, fields=['TR'], labels=False)

    custom_legend_html = ""; has_custom = False; current_opacity = 1.0

    if one_bundle:
        sel_one, one_conf = one_bundle
        for name in sel_one:
            if name not in available_dict: continue
            c = one_conf[name]; v_min, v_max = float(c.get('vmin', 0)), float(c.get('vmax', 100))
            if not c.get('visible', True): continue
            
            # MATRİS VE PNG (Cached)
            rgba, bnds = get_cached_rgba(available_dict[name], v_min, v_max, 
                                         (c['one_c'] if c.get('sub_mode') == "One-Color" else c.get('cmap', 'viridis')), 
                                         c['mode'], c.get('thresh'), c.get('b_c'), c.get('a_c'), 
                                         c.get('b_m') == "No Color", c.get('a_m') == "No Color")
            
            png_url = rgba_to_png_base64(rgba)
            ImageOverlay(image=png_url, bounds=bnds, opacity=c['alpha'], name=name, zindex=5).add_to(m)
            
            # Opacity değerini loop dışına taşımak için saklıyoruz
            current_opacity = c['alpha']

            # Lejant Basamakları (Daha önce yaptığımız Hayalet 0 fix duruyor)
            unit = units_dict.get(name, ""); colorbar_title = f"{name} ({unit})" if unit else name
            if c['mode'] == "Interval" and c.get('sub_mode') == "Multi-Color":
                n_lv = int(c.get('lv', 5)); bins = np.linspace(v_min, v_max, n_lv + 1)
                colors = [mpl.colors.rgb2hex(plt.get_cmap(c['cmap'])(i)) for i in np.linspace(0, 1, n_lv)]
                m.add_child(cm.StepColormap(colors, vmin=v_min, vmax=v_max, index=bins, caption=colorbar_title))
            elif c['mode'] == "Interval":
                custom_legend_html += f'<div style="display:flex;align-items:center;margin-bottom:6px;"><div style="width:18px;height:18px;background:{c["one_c"]};margin-right:10px;"></div><span style="color:black; font-size:14px;">{name}: {v_min:.0f}-{v_max:.0f}</span></div>'; has_custom = True

    # LOOP DIŞINDA TEK CSS ENJEKSİYONU
    m.get_root().header.add_child(folium.Element(f"<style>.legend {{ opacity: {current_opacity} !important; }}</style>"))

    if has_custom:
        m.get_root().html.add_child(folium.Element(f'<div style="position:fixed; bottom:35px; right:40px; z-index:9999; background:rgba(255,255,255,0.9); padding:12px; border-radius:8px; box-shadow: 0 0 10px rgba(0,0,0,0.2); min-width:220px;">{custom_legend_html}</div>'))
    
    m.add_layer_control()
    return m