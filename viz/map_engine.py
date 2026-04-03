import streamlit as st
import leafmap.foliumap as leafmap
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import branca.colormap as cm
import folium
from folium.raster_layers import ImageOverlay 

@st.cache_data(show_spinner=False)
def get_cached_rgba(file_name, vmin, vmax, cmap_input, mode, thresh=None, color_below=None, color_above=None, no_b=False, no_a=False):
    from core.data_loader import load_index_data
    data, _, _ = load_index_data(file_name)
    vals = data.values
    mask = ~np.isnan(vals)
    rgba = np.zeros((*vals.shape, 4), dtype=np.float32)

    if mode == "Threshold":
        t = thresh
        if not no_b: 
            idx_below = mask & (vals < t)
            rgba[idx_below, :3] = mpl.colors.to_rgba(color_below)[:3]
            rgba[idx_below, 3] = 1.0
        if not no_a: 
            idx_above = mask & (vals > t)
            rgba[idx_above, :3] = mpl.colors.to_rgba(color_above)[:3]
            rgba[idx_above, 3] = 1.0
    else:
        # Range dışındaki yerlerin şeffaf kalması için sadece valid_range'i boyuyoruz
        valid_range = mask & (vals >= vmin) & (vals <= vmax)
        if isinstance(cmap_input, str) and cmap_input.startswith('#'):
            rgba[valid_range, :3] = mpl.colors.to_rgba(cmap_input)[:3]
        else:
            norm = plt.Normalize(vmin=vmin, vmax=vmax)
            cmap = plt.get_cmap(cmap_input)
            rgba[valid_range, :3] = cmap(norm(vals[valid_range]))[:, :3]
        rgba[valid_range, 3] = 1.0 
    
    left, bottom, right, top = data.rio.transform_bounds("EPSG:4326")
    return (rgba * 255).astype(np.uint8), [[bottom, left], [top, right]]

@st.cache_data(show_spinner=False)
def get_synthesis_rgba(names, vmin_list, vmax_list, color):
    from core.data_loader import load_index_data
    combined_mask = None
    ref_data = None
    for i, name in enumerate(names):
        curr, _, _ = load_index_data(name)
        if ref_data is None: ref_data = curr
        v_min, v_max = vmin_list[i], vmax_list[i]
        mask = (curr.values >= v_min) & (curr.values <= v_max) if curr.shape == ref_data.shape else \
               (curr.reindex_like(ref_data, method="nearest").values >= v_min) & (curr.reindex_like(ref_data, method="nearest").values <= v_max)
        combined_mask = mask if combined_mask is None else combined_mask & mask
    
    if combined_mask is not None:
        rgba = np.zeros((*combined_mask.shape, 4), dtype=np.float32)
        rgba[combined_mask, :3] = mpl.colors.to_rgba(color)[:3]
        rgba[combined_mask, 3] = 1.0
        left, bottom, right, top = ref_data.rio.transform_bounds("EPSG:4326")
        return (rgba * 255).astype(np.uint8), [[bottom, left], [top, right]]
    return None, None

def create_interactive_map(shp, one_bundle, multi_bundle, units_dict, available_dict):
    m = leafmap.Map(
        center=st.session_state.get('map_center', [38.9, 35.5]), 
        zoom=st.session_state.get('map_zoom', 5), 
        tiles=None, control_scale=True
    )

    # --- CSS CONFIGURATION (İLMEK İLMEK İŞLEDİĞİN KISIM - DOKUNULMADI) ---
    m.get_root().header.add_child(folium.Element("""
    <style>
    .leaflet-image-layer, .leaflet-raster-layer {
        image-rendering: -webkit-optimize-contrast !important;
        image-rendering: crisp-edges !important;
        image-rendering: pixelated !important;
    }
    .leaflet-tooltip table th { display: none !important; }
    .leaflet-tooltip table td { font-weight: bold !important; font-size: 14px !important; }
    .legend {
        font-size: 16px !important;
        font-weight: normal !important;
        display: flex !important;
        flex-direction: column-reverse !important; 
        align-items: center !important;
        background: none !important;
        border: none !important;
        box-shadow: none !important;
        padding: 10px !important;
        overflow: visible !important;
    }
    .legend .caption {
        font-size: 16px !important;
        font-weight: normal !important;
        text-align: center !important;
        display: block !important;
        color: black !important;
        transform: translateY(3px) !important; 
        margin-bottom: 30px !important; 
        line-height: 1.5 !important;
    }
    .legend svg { margin-bottom: 15px !important; overflow: visible !important; }
    .legend svg text { font-weight: normal !important; font-size: 16px !important; fill: black !important; }
    .leaflet-top.leaflet-right {
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-end !important;
        gap: 10px !important;
    }
    </style>
    """))
    
    if shp is not None:
        temp_shp = shp[['ADM1_TR', 'geometry']].copy(); temp_shp.columns = ['TR', 'geometry']
        m.add_gdf(temp_shp, layer_name="Türkiye Provinces", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.0}, fields=['TR'], labels=False)

    custom_legend_html = ""
    has_custom = False

    if one_bundle:
        sel_one, one_conf = one_bundle
        for name in sel_one:
            if name not in available_dict: continue
            c = one_conf[name]
            if not c.get('visible', True): continue
            v_min, v_max = float(c.get('vmin', 0)), float(c.get('vmax', 100))
            
            # --- ONE-COLOR MANTIĞI ---
            visual_input = c['one_c'] if c.get('sub_mode') == "One-Color" else c.get('cmap', 'viridis')
            
            rgba_uint8, bnds = get_cached_rgba(
                available_dict[name], v_min, v_max, visual_input, c['mode'],
                c.get('thresh'), c.get('b_c'), c.get('a_c'), c.get('b_m') == "No Color", c.get('a_m') == "No Color"
            )
            
            ImageOverlay(image=rgba_uint8, bounds=bnds, opacity=c['alpha'], name=name, zindex=5).add_to(m)
            
            m.get_root().header.add_child(folium.Element(f"""
            <style>
                .legend {{ opacity: {c['alpha']} !important; transition: opacity 0.3s; }}
            </style>
            """))

            # --- LEJANT KODLARI (DİNAMİK LV/LEVEL DÜZELTMESİ) ---
            unit = units_dict.get(name, ""); colorbar_title = f"{name} ({unit})" if unit else name
            if c['mode'] == "Interval" and c.get('sub_mode') == "Multi-Color":
                if c.get('disc'):

                    n_lv = int(c.get('lv', 5))
                    bins = np.linspace(v_min, v_max, n_lv + 1)
                    colors = [mpl.colors.rgb2hex(plt.get_cmap(c['cmap'])(i)) for i in np.linspace(0, 1, n_lv)]
                    
                    m.add_child(cm.StepColormap(colors, vmin=v_min, vmax=v_max, index=bins, caption=colorbar_title))
                else:
                    colors = [mpl.colors.rgb2hex(plt.get_cmap(c['cmap'])(i)) for i in np.linspace(0, 1, 256)]
                    ticks = np.linspace(v_min, v_max, 6)
                    m.add_child(cm.LinearColormap(colors=colors, vmin=v_min, vmax=v_max, caption=colorbar_title).to_step(index=ticks))
            elif c['mode'] == "Interval":
                custom_legend_html += f'<div style="display:flex;align-items:center;margin-bottom:6px;"><div style="width:18px;height:18px;background:{c["one_c"]};margin-right:10px;"></div><span style="color:black; font-size:14px;">{name}: {v_min:.0f}-{v_max:.0f}</span></div>'
                has_custom = True

    # --- Section 2: Synthesis ---
    if st.session_state.get('synthesis_active') and multi_bundle[0]:
        sel_multi, multi_conf = multi_bundle
        names = [available_dict[n] for n in sel_multi]
        vmin_list = [multi_conf['indices'][n]['vmin'] for n in sel_multi]
        vmax_list = [multi_conf['indices'][n]['vmax'] for n in sel_multi]
        
        synth_rgba, bnds = get_synthesis_rgba(tuple(names), tuple(vmin_list), tuple(vmax_list), multi_conf['color'])
        
        if synth_rgba is not None:
            ImageOverlay(image=synth_rgba, bounds=bnds, opacity=multi_conf['alpha'], name="MULTI INDICES", zindex=6).add_to(m)
            m.get_root().header.add_child(folium.Element(f"""
            <style>
                .legend {{ opacity: {multi_conf['alpha']} !important; }}
            </style>
            """))
            synth_rows = "".join([f'<div style="display:flex;align-items:center;margin-bottom:4px;"><div style="width:18px;height:18px;background:{multi_conf["color"] if i==0 else "transparent"};margin-right:10px;"></div><span style="color:black; font-size:14px;">{name}: {multi_conf["indices"][name]["vmin"]:.0f}-{multi_conf["indices"][name]["vmax"]:.0f}</span></div>' for i, name in enumerate(sel_multi)])
            separator = 'border-top:1px solid #ccc; margin-top:10px; padding-top:10px;' if custom_legend_html else ''
            custom_legend_html += f'<div style="{separator}">{synth_rows}</div>'
            has_custom = True

    if has_custom:
        m.get_root().html.add_child(folium.Element(f'<div style="position:fixed; bottom:35px; right:40px; z-index:9999; background:rgba(255,255,255,0.9); padding:12px; border-radius:8px; box-shadow: 0 0 10px rgba(0,0,0,0.2); min-width:220px;">{custom_legend_html}</div>'))
    
    m.add_layer_control()
    return m