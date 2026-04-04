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

# --- AŞAMA 1: DISK OKUMA CACHE (TIF dosyasını RAM'e sadece 1 kez alır) ---
@st.cache_data(show_spinner=False)
def load_raw_data(file_name):
    from core.data_loader import load_index_data
    data, _, _ = load_index_data(file_name)
    return data

# --- AŞAMA 2: PNG ENCODE CACHE (Hızlı render için resmi önceden hazırlar) ---
@st.cache_data(show_spinner=False)
def rgba_to_png_base64(rgba_uint8):
    img = Image.fromarray(rgba_uint8)
    buf = io.BytesIO()
    img.save(buf, format="PNG") 
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

# --- AŞAMA 3: RENKLENDİRME MOTORU (RAM üzerinden çalışır) ---
@st.cache_data(show_spinner=False)
def get_cached_rgba(file_name, vmin, vmax, cmap_input, mode, thresh=None, color_below=None, color_above=None, no_b=False, no_a=False):
    data = load_raw_data(file_name) 
    vals = data.values
    mask = ~np.isnan(vals); rgba = np.zeros((*vals.shape, 4), dtype=np.float32)

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

# --- SENTEZ MOTORU ---
@st.cache_data(show_spinner=False)
def get_synthesis_rgba(names, vmin_list, vmax_list, color):
    combined_mask = None; ref_data = None
    for i, name in enumerate(names):
        curr = load_raw_data(name)
        if ref_data is None: ref_data = curr
        mask = (curr.values >= vmin_list[i]) & (curr.values <= vmax_list[i]) if curr.shape == ref_data.shape else \
               (curr.reindex_like(ref_data, method="nearest").values >= vmin_list[i]) & (curr.reindex_like(ref_data, method="nearest").values <= vmax_list[i])
        combined_mask = mask if combined_mask is None else combined_mask & mask
    
    if combined_mask is not None:
        rgba = np.zeros((*combined_mask.shape, 4), dtype=np.float32)
        rgba[combined_mask, :3] = mpl.colors.to_rgba(color)[:3]; rgba[combined_mask, 3] = 1.0
        left, bottom, right, top = ref_data.rio.transform_bounds("EPSG:4326")
        return (rgba * 255).astype(np.uint8), [[bottom, left], [top, right]]
    return None, None

def create_interactive_map(shp, one_bundle, multi_bundle, units_dict, available_dict):
    m = leafmap.Map(center=st.session_state.get('map_center', [38.9, 35.5]), zoom=st.session_state.get('map_zoom', 5), tiles=None, control_scale=True)

    # --- CSS: LEJANT MESAFLERİ VE YAZI DÜZENİ ---
    m.get_root().header.add_child(folium.Element("""
    <style>
    .leaflet-image-layer, .leaflet-raster-layer { image-rendering: pixelated !important; }
    
    /* Her lejant kutusunun arası (Colorbarlar arası mesafe) */
    .legend { 
        margin-bottom: 25px !important; 
        font-size: 16px !important; 
        display: flex !important; 
        flex-direction: column-reverse !important; 
        align-items: center !important; 
        opacity: 1 !important; /* Her zaman %100 opak */
    }
    
    /* Başlık (Caption) ve Bar arasındaki mesafe */
    .legend .caption { 
        font-size: 16px !important; 
        color: black !important; 
        margin-bottom: 5px !important; 
        transform: translateY(3px) !important;
        line-height: 1.2 !important;
    }
    
    /* Bar (SVG) ve altındaki rakamlar arasındaki mesafe */
    .legend svg { 
        margin-bottom: 5px !important; 
        opacity: 1 !important; /* Her zaman %100 opak */
    }
    
    .legend svg text { fill: black !important; font-weight: bold !important; font-size: 14px !important; }
    
    .leaflet-top.leaflet-right { display: flex !important; flex-direction: column !important; align-items: flex-end !important; gap: 15px !important; }
    </style>
    """))
    
    if shp is not None:
        temp_shp = shp[['ADM1_TR', 'geometry']].copy(); temp_shp.columns = ['TR', 'geometry']
        m.add_gdf(temp_shp, layer_name="Türkiye Provinces", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.0}, labels=False)

    custom_legend_html = ""; has_custom = False

    if one_bundle:
        sel_one, one_conf = one_bundle
        for name in sel_one:
            if name not in available_dict: continue
            c = one_conf[name]; v_min, v_max = float(c.get('vmin', 0)), float(c.get('vmax', 100))
            if not c.get('visible', True): continue
            
            # Veri ve PNG Hazırla
            rgba, bnds = get_cached_rgba(available_dict[name], v_min, v_max, (c['one_c'] if c.get('sub_mode') == "One-Color" else c.get('cmap', 'viridis')), c['mode'], c.get('thresh'), c.get('b_c'), c.get('a_c'), c.get('b_m') == "No Color", c.get('a_m') == "No Color")
            png_url = rgba_to_png_base64(rgba)
            ImageOverlay(image=png_url, bounds=bnds, opacity=c['alpha'], name=name, zindex=5).add_to(m)
            
            # LEJANT KODLARI
            unit = units_dict.get(name, ""); colorbar_title = f"{name} ({unit})" if unit else name
            if c['mode'] == "Interval" and c.get('sub_mode') == "Multi-Color":
                n_lv = int(c.get('lv', 5)); bins = np.linspace(v_min, v_max, n_lv + 1)
                colors = [mpl.colors.rgb2hex(plt.get_cmap(c['cmap'])(i)) for i in np.linspace(0, 1, n_lv)]
                m.add_child(cm.StepColormap(colors, vmin=v_min, vmax=v_max, index=bins, caption=colorbar_title))
            elif c['mode'] == "Interval":
                custom_legend_html += f'<div style="display:flex;align-items:center;margin-bottom:8px;"><div style="width:20px;height:20px;background:{c["one_c"]};margin-right:10px; border:1px solid black; opacity:1;"></div><span style="color:black; font-size:15px; font-weight:bold;">{name}: {v_min:.0f}-{v_max:.0f}</span></div>'; has_custom = True

    # Section 2: Synthesis (Aynı Mantık)
    if st.session_state.get('synthesis_active') and multi_bundle[0]:
        sel_multi, multi_conf = multi_bundle
        s_rgba, bnds = get_synthesis_rgba(tuple([available_dict[n] for n in sel_multi]), tuple([multi_conf['indices'][n]['vmin'] for n in sel_multi]), tuple([multi_conf['indices'][n]['vmax'] for n in sel_multi]), multi_conf['color'])
        if s_rgba is not None:
            s_png = rgba_to_png_base64(s_rgba)
            ImageOverlay(image=s_png, bounds=bnds, opacity=multi_conf['alpha'], name="MULTI INDICES", zindex=6).add_to(m)
            synth_rows = "".join([f'<div style="display:flex;align-items:center;margin-bottom:5px;"><div style="width:20px;height:20px;background:{multi_conf["color"] if i==0 else "transparent"};margin-right:10px; border:{ "1px solid black" if i==0 else "none"};"></div><span style="color:black; font-size:15px; font-weight:bold;">{name}: {multi_conf["indices"][name]["vmin"]:.0f}-{multi_conf["indices"][name]["vmax"]:.0f}</span></div>' for i, name in enumerate(sel_multi)])
            custom_legend_html += f'<div style="border-top:2px solid #333; margin-top:10px; padding-top:10px;">{synth_rows}</div>'; has_custom = True

    if has_custom:
        m.get_root().html.add_child(folium.Element(f'<div style="position:fixed; bottom:40px; right:40px; z-index:9999; background:rgba(255,255,255,0.95); padding:15px; border-radius:10px; border:2px solid #333; box-shadow: 5px 5px 15px rgba(0,0,0,0.3); min-width:240px;">{custom_legend_html}</div>'))
    
    m.add_layer_control()
    return m