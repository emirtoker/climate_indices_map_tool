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

def get_clean_label(file_name, prefix=""):
    """
    Dosya isminden indisi (PCD, DI, UTCI vb.) hatasız yakalar.
    Kısaltmayı her zaman BÜYÜK HARF yapar, açıklamayı Title Case yapar.
    """
    codes = ["PCD", "PRCPTOT", "SU", "TR", "DI", "HI", "PET", "SPI", "SPEI", "UTCI"]
    clean = file_name.replace(".tif", "").replace("_cog", "")
    parts = clean.split('_')
    
    found_code, found_idx = None, -1
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].upper() in codes:
            if parts[i].upper() == "TR" and i < 4: continue
            found_code = parts[i].upper()
            found_idx = i
            break
            
    if found_code:
        description = " ".join(parts[found_idx + 1:]).replace("_", " ").title()
        label = f"{found_code} - {description}"
    else:
        label = clean.replace("_", " ").title()
        
    return f"{prefix}{label}" if prefix else label

# --- AŞAMA 1: RAM KONTROLLÜ OKUMA ---
@st.cache_data(show_spinner=False, max_entries=5)
def load_raw_data(file_name):
    from core.data_loader import load_index_data
    data, _, _ = load_index_data(file_name)
    return data

# --- AŞAMA 2: ULTRA HAFİF PNG ENCODE ---
@st.cache_data(show_spinner=False, max_entries=10)
def rgba_to_png_base64(rgba_uint8):
    img = Image.fromarray(rgba_uint8)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True) 
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

# --- AŞAMA 3: AKILLI RENKLENDİRME (EXTEND DESTEKLİ) ---
@st.cache_data(show_spinner=False, max_entries=5)
def get_cached_rgba(file_name, vmin, vmax, cmap_input, mode, thresh=None, color_below=None, color_above=None, no_b=False, no_a=False, ext_min=True, ext_max=True):
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
        # Eğer vmin == vmax ise hata vermemesi için küçük bir koruma
        if vmin == vmax: vmax += 0.001
        
        cmap = plt.get_cmap(cmap_input)
        norm = plt.Normalize(vmin=vmin, vmax=vmax)
        
        # 1. Normal Aralık (vmin - vmax)
        valid = mask & (vals >= vmin) & (vals <= vmax)
        rgba[valid, :3] = cmap(norm(vals[valid]))[:, :3]
        rgba[valid, 3] = 1.0
        
        # 2. Extend Min: vmin'den küçükleri en alt renge boya
        if ext_min:
            low = mask & (vals < vmin)
            rgba[low, :3] = cmap(0.0)[:3]
            rgba[low, 3] = 1.0
            
        # 3. Extend Max: vmax'tan büyükleri en üst renge boya
        if ext_max:
            high = mask & (vals > vmax)
            rgba[high, :3] = cmap(1.0)[:3]
            rgba[high, 3] = 1.0
    
    left, bottom, right, top = data.rio.transform_bounds("EPSG:4326")
    return (rgba * 255).astype(np.uint8), [[bottom, left], [top, right]]

# Sentez Motoru (Dinamik maskeleme)
@st.cache_data(show_spinner=False, max_entries=3)
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

    # --- CSS: LEJANT VE YAZI DÜZENİ ---
    m.get_root().header.add_child(folium.Element("""
    <style>
    .leaflet-image-layer, .leaflet-raster-layer { image-rendering: pixelated !important; }
    
    .legend { 
        margin-bottom: 30px !important; 
        font-size: 16px !important; 
        display: flex !important; 
        flex-direction: column-reverse !important; 
        align-items: center !important; 
        opacity: 1 !important; 
        overflow: visible !important;
        height: auto !important;
        min-height: 90px !important;
    }
    
    .legend .caption { 
        font-size: 16px !important; 
        color: black !important; 
        margin-bottom: 5px !important; 
        line-height: 1.2 !important; 
        font-weight: bold !important;
        transform: translateY(8px) !important;
        overflow: visible !important;
    }
    
    .legend svg { 
        margin-bottom: 10px !important; 
        opacity: 1 !important; 
        overflow: visible !important;
    }
    
    .legend svg text { 
        fill: black !important; 
        font-weight: bold !important; 
        font-size: 14px !important; 
    }
    
    .leaflet-top.leaflet-right { 
        display: flex !important; 
        flex-direction: column !important; 
        align-items: flex-end !important; 
        gap: 25px !important; 
    }
    </style>
    """))
    
    if shp is not None:
        temp_shp = shp[['ADM1_TR', 'geometry']].copy(); temp_shp.columns = ['TR', 'geometry']
        m.add_gdf(temp_shp, layer_name="Türkiye Provinces", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.0}, labels=False)

    custom_legend_html = ""; has_custom = False

    # --- 1. SINGLE INDICE ---
    if one_bundle:
        sel_one, one_conf = one_bundle
        for name in sel_one:
            if name not in available_dict: continue
            c = one_conf[name]
            if not c.get('visible', True): continue
            
            # Veriyi renklendir
            rgba, bnds = get_cached_rgba(
                available_dict[name], c['vmin'], c['vmax'], 
                (c['one_c'] if c.get('sub_mode') == "One-Color" else c.get('cmap', 'viridis')), 
                c['mode'], c.get('thresh'), c.get('b_c'), c.get('a_c'), 
                c.get('b_m') == "No Color", c.get('a_m') == "No Color",
                c.get('ext_min', True), c.get('ext_max', True)
            )
            ImageOverlay(image=rgba_to_png_base64(rgba), bounds=bnds, opacity=c['alpha'], name=name, zindex=5).add_to(m)
            
            # Başlık Hazırla
            prefix = c.get('legend_prefix', "")
            clean_name = get_clean_label(name, prefix)
            unit = units_dict.get(name, "")
            colorbar_title = f"{clean_name} ({unit})" if unit else clean_name
            
            if c['mode'] == "Interval" and c.get('sub_mode') == "Multi-Color":
                n_lv = int(c.get('lv', 10))
                bins = [float(x) for x in np.linspace(c['vmin'], c['vmax'], n_lv + 1)]
                colors = [mpl.colors.rgb2hex(plt.get_cmap(c['cmap'])(i)) for i in np.linspace(0, 1, n_lv)]
                m.add_child(cm.StepColormap(
                    colors, 
                    vmin=bins[0], 
                    vmax=bins[-1], 
                    index=bins, 
                    caption=colorbar_title
                ))
                
            elif c['mode'] == "Interval":
                line = '<div style="border-top:1px solid #ccc; margin:8px 0;"></div>' if custom_legend_html else ""
                custom_legend_html += f'{line}<div style="display:flex;align-items:center;margin-bottom:8px;"><div style="width:20px;height:20px;background:{c["one_c"]};margin-right:10px; border:1px solid black;"></div><span style="color:black; font-size:15px; font-weight:bold;">{clean_name}: {c["vmin"]:.0f}-{c["vmax"]:.0f}</span></div>'
                has_custom = True

    # --- 2. MULTI INDICES ---
    if st.session_state.get('synthesis_active') and multi_bundle[0]:
        sel_multi, multi_conf = multi_bundle
        s_rgba, bnds = get_synthesis_rgba(tuple([available_dict[n] for n in sel_multi]), tuple([multi_conf['indices'][n]['vmin'] for n in sel_multi]), tuple([multi_conf['indices'][n]['vmax'] for n in sel_multi]), multi_conf['color'])
        if s_rgba is not None:
            ImageOverlay(image=rgba_to_png_base64(s_rgba), bounds=bnds, opacity=multi_conf['alpha'], name="MULTI INDICES", zindex=6).add_to(m)
            
            if custom_legend_html: custom_legend_html += '<div style="border-top:2px solid #333; margin:10px 0; padding-top:10px;"></div>'
            
            synth_rows = ""
            for i, name in enumerate(sel_multi):
                display_name = multi_conf['indices'][name].get('legend_name', get_clean_label(name))
                v_min_m = multi_conf['indices'][name]['vmin']
                v_max_m = multi_conf['indices'][name]['vmax']
                color_box = multi_conf["color"] if i == 0 else "transparent"
                border = "1px solid black" if i == 0 else "none"
                synth_rows += f'<div style="display:flex;align-items:center;margin-bottom:5px;"><div style="width:20px;height:20px;background:{color_box};margin-right:10px; border:{border};"></div><span style="color:black; font-size:15px; font-weight:bold;">{display_name}: {v_min_m:.0f}-{v_max_m:.0f}</span></div>'
            
            custom_legend_html += f'<div>{synth_rows}</div>'; has_custom = True

    if has_custom:
        m.get_root().html.add_child(folium.Element(f'<div style="position:fixed; bottom:40px; right:40px; z-index:9999; background:rgba(255,255,255,0.95); padding:15px; border-radius:10px; border:2px solid #333; box-shadow: 5px 5px 15px rgba(0,0,0,0.3); min-width:240px;">{custom_legend_html}</div>'))
    
    m.add_layer_control()
    return m