import streamlit as st
import leafmap.foliumap as leafmap
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import xarray as xr
import branca.colormap as cm
import folium

def create_interactive_map(layers, shp, one_bundle, multi_bundle, units_dict):
    # Haritayı notebook'taki gibi milimetrik çakışma için hazırlıyoruz
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None, control_scale=True, zoom_snap=0.1, zoom_delta=0.1)
    
    # --- SENİN MÜHÜRLÜ CSS AYARLARIN (DOKUNULMAZ) ---
    m.get_root().header.add_child(folium.Element("""
    <style>
    .leaflet-image-layer, .leaflet-raster-layer {
        image-rendering: -webkit-optimize-contrast !important;
        image-rendering: crisp-edges !important;
        image-rendering: pixelated !important;
    }
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
        font-style: normal !important;
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
    .leaflet-control-layers { margin-top: 10px !important; margin-right: 10px !important; }
    .leaflet-control-layers-toggle { width: 36px !important; height: 36px !important; background-size: 20px 20px !important; }
    </style>
    """))
    
    # SHP Katmanı (En üstte kalması için zindex ayarlı)
    if shp is not None:
        m.add_gdf(shp, layer_name="Administrative Boundaries", style={'color': 'black', 'fillOpacity': 0, 'weight': 0.8})
    
    custom_legend_html = ""
    has_custom = False

    # --- KRİTİK: MILIMETRIC RASTER ENGINE ---
    def add_accurate_raster(map_obj, data_arr, cmap_name, layer_name, vmin, vmax, alpha):
        """
        Notebook'taki pcolormesh gibi milimetrik hizalama yapar.
        Koordinat sistemini (CRS) zorlar ve pikselleri kaydırmaz.
        """
        try:
            # Projeksiyonu mühürle (Kaymayı engellemek için)
            if data_arr.rio.crs is None:
                data_arr.rio.write_crs("EPSG:4326", inplace=True)
            
            # Palette hazırlığı
            if isinstance(cmap_name, str):
                cmap = plt.get_cmap(cmap_name)
                palette = [mpl.colors.rgb2hex(cmap(i)) for i in np.linspace(0, 1, 256)]
            else:
                # ListedColormap (Threshold/One-Color için)
                palette = [mpl.colors.rgb2hex(cmap_name.colors[0])] * 2

            # add_raster: ImageOverlay yerine bunu kullanarak pikselleri gerçek koordinatına çiviliyoruz
            map_obj.add_raster(
                data_arr, 
                palette=palette, 
                vmin=vmin, 
                vmax=vmax, 
                layer_name=layer_name, 
                opacity=alpha,
                nodata=np.nan
            )
        except Exception as e:
            st.error(f"Raster alignment error on {layer_name}: {e}")

    # --- 1. SINGLE INDEX ---
    if one_bundle:
        sel_one, one_conf = one_bundle
        for name in sel_one:
            if name not in layers: continue
            c = one_conf[name]
            if not c.get('visible', True): continue
            
            data = layers[name].copy()
            if 'time' in data.dims: data = data.mean('time')
            
            u_str = f"({c['unit']})" if c['unit'] else ""
            vmin_val, vmax_val = float(c['vmin']), float(c['vmax'])

            if c['mode'] == "Threshold":
                t = c['thresh']
                if c.get('b_m') == "Color":
                    b_data = data.where(data < t, np.nan)
                    add_accurate_raster(m, b_data, mpl.colors.ListedColormap([c['b_c']]), f"{name} Below", t-1, t, c['alpha'])
                    custom_legend_html += f'<div style="display:flex;align-items:center;margin-bottom:6px;"><div style="width:18px;height:18px;background:{c["b_c"]};margin-right:10px;"></div><span style="font-size:14px;color:black;">{name} < {t:.0f} {u_str}</span></div>'
                    has_custom = True
                if c.get('a_m') == "Color":
                    a_data = data.where(data > t, np.nan)
                    add_accurate_raster(m, a_data, mpl.colors.ListedColormap([c['a_c']]), f"{name} Above", t, t+1, c['alpha'])
                    custom_legend_html += f'<div style="display:flex;align-items:center;margin-bottom:6px;"><div style="width:18px;height:18px;background:{c["a_c"]};margin-right:10px;"></div><span style="font-size:14px;color:black;">{name} > {t:.0f} {u_str}</span></div>'
                    has_custom = True
            else:
                if c.get('sub_mode') == "Multi-Color":
                    if c.get('disc'):
                        n_lv = int(c['lv'])
                        bins = np.linspace(vmin_val, vmax_val, n_lv + 1)
                        idx = np.digitize(data.values, bins) - 1
                        idx = np.clip(idx, 0, n_lv - 1)
                        bin_centers = (bins[:-1] + bins[1:]) / 2
                        data_disc = xr.DataArray(bin_centers[idx], coords=data.coords, dims=data.dims)
                        data_disc = data_disc.where(data.notnull(), np.nan)
                        
                        add_accurate_raster(m, data_disc, c['cmap'], name, vmin_val, vmax_val, c['alpha'])
                        colors = [mpl.colors.rgb2hex(plt.get_cmap(c['cmap'])(i)) for i in np.linspace(0, 1, n_lv)]
                        m.add_child(cm.StepColormap(colors, vmin=vmin_val, vmax=vmax_val, index=bins, caption=f"{name} {u_str}"))
                    else:
                        add_accurate_raster(m, data, c['cmap'], name, vmin_val, vmax_val, c['alpha'])
                        colors = [mpl.colors.rgb2hex(plt.get_cmap(c['cmap'])(i)) for i in np.linspace(0, 1, 256)]
                        cmap_obj = cm.LinearColormap(colors=colors, vmin=vmin_val, vmax=vmax_val, caption=f"{name} {u_str}")
                        m.add_child(cmap_obj.to_step(index=np.linspace(vmin_val, vmax_val, 6)))
                else:
                    d_one = data.where((data >= vmin_val) & (data <= vmax_val), np.nan)
                    add_accurate_raster(m, d_one, mpl.colors.ListedColormap([c['one_c']]), name, vmin_val, vmax_val, c['alpha'])
                    custom_legend_html += f'<div style="display:flex;align-items:center;margin-bottom:6px;"><div style="width:18px;height:18px;background:{c["one_c"]};margin-right:10px;"></div><span style="font-size:14px;color:black;">{name}: {vmin_val:.0f}-{vmax_val:.0f} {u_str}</span></div>'
                    has_custom = True

    # --- 2. SYNTHESIS ---
    if st.session_state.get('synthesis_active') and multi_bundle[0]:
        sel_multi, multi_conf = multi_bundle
        if sel_multi and sel_multi[0] in layers:
            ref_data = layers[sel_multi[0]].copy()
            if 'time' in ref_data.dims: ref_data = ref_data.mean('time')
            combined_mask = None
            synth_rows = ""
            for i, name in enumerate(sel_multi):
                if name not in layers: continue
                curr = layers[name].copy()
                if 'time' in curr.dims: curr = curr.mean('time')
                curr = curr.reindex_like(ref_data, method="nearest")
                v_min, v_max = multi_conf['indices'][name]['vmin'], multi_conf['indices'][name]['vmax']
                mask = (curr >= v_min) & (curr <= v_max)
                combined_mask = mask if combined_mask is None else combined_mask & mask
                u_str_m = f"({units_dict.get(name, '')})" if units_dict.get(name) else ""
                color_box = f'<div style="width:18px;height:18px;background:{multi_conf["color"]};margin-right:10px;"></div>' if i==0 else '<div style="width:18px;height:18px;margin-right:10px;"></div>'
                synth_rows += f'<div style="display:flex;align-items:center;margin-bottom:4px;">{color_box}<span style="font-size:14px;color:black;">{name}: {v_min:.0f}-{v_max:.0f} {u_str_m}</span></div>'
            if combined_mask is not None:
                synth = ref_data.where(combined_mask, np.nan)
                add_accurate_raster(m, synth, mpl.colors.ListedColormap([multi_conf['color']]), "Synthesis Result", 0, 1, multi_conf['alpha'])
                custom_legend_html += f'<div style="margin-top:10px;">{synth_rows}</div>'
                has_custom = True

    if has_custom:
        legend_div = f'<div style="position:fixed; bottom:35px; right:40px; z-index:9999; background:none; border:none; padding:0; min-width:280px;">{custom_legend_html}</div>'
        m.get_root().html.add_child(folium.Element(legend_div))
    
    m.add_layer_control()
    return m