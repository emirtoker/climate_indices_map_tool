import streamlit as st
import leafmap.foliumap as leafmap
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import xarray as xr
import branca.colormap as cm
import folium
import rioxarray

def create_interactive_map(layers, shp, one_bundle, multi_bundle, units_dict):
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None, control_scale=True, zoom_snap=0.1, zoom_delta=0.1)
    
    # Custom CSS for high-contrast raster rendering and legend formatting
    m.get_root().header.add_child(folium.Element("""
    <style>
    .leaflet-image-layer, .leaflet-raster-layer {
        image-rendering: -webkit-optimize-contrast !important;
        image-rendering: crisp-edges !important;
        image-rendering: pixelated !important;
    }
    /* Standardizes the Leaflet legend container */
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
    /* Vertical offset for colorbar title - adjust translateY to move up/down */
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
    .legend svg {
        margin-bottom: 15px !important;
        overflow: visible !important;
    }
    .legend svg text {
        font-weight: normal !important;
        font-size: 16px !important;
        fill: black !important;
    }
    /* Fix: Prevents layer control box from stretching. Uses flex instead of grid. */
    .leaflet-top.leaflet-right {
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-end !important;
        gap: 10px !important;
    }
    /* Ensures the layer control square icon remains independent and small */
    .leaflet-control-layers {
        margin-top: 10px !important;
        margin-right: 10px !important;
    }
    .leaflet-control-layers-toggle { 
        width: 36px !important; 
        height: 36px !important; 
        background-size: 20px 20px !important; 
    }
    </style>
    """))
    
    # Boundary Layer
    if shp is not None:
        m.add_gdf(shp, layer_name="Türkiye Provinces", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.2})
    
    custom_legend_html = ""
    has_custom = False

    # 1. Single Index Visualization Logic
    if one_bundle:
        sel_one, one_conf = one_bundle
        for name in sel_one:
            c = one_conf[name]
            if not c.get('visible', True): continue
            data = layers[name].copy()
            if 'time' in data.dims: data = data.mean('time')
            
            # CRS persistence check
            if data.rio.crs is None:
                data.rio.write_crs("EPSG:4326", inplace=True)
            
            # Spatial Clipping via Shapefile
            if shp is not None:
                data = data.rio.clip(shp.geometry, shp.crs, drop=False)
                data = data.where(data.notnull(), np.nan)

            u_str = f"({c['unit']})" if c['unit'] else ""

            # Threshold Mode (Binary Masking)
            if c['mode'] == "Threshold":
                t = c['thresh']
                if c.get('b_m') == "Color":
                    b_data = data.where(data < t, np.nan)
                    m.add_raster(b_data, palette=[c['b_c'], c['b_c']], layer_name=f"{name} Below", opacity=c['alpha'], nodata=np.nan)
                    custom_legend_html += f'<div style="display:flex;align-items:center;margin-bottom:6px;"><div style="width:18px;height:18px;background:{c["b_c"]};margin-right:10px;"></div><span style="font-size:14px;color:black;">{name} < {t:.0f} {u_str}</span></div>'
                    has_custom = True
                if c.get('a_m') == "Color":
                    a_data = data.where(data > t, np.nan)
                    m.add_raster(a_data, palette=[c['a_c'], c['a_c']], layer_name=f"{name} Above", opacity=c['alpha'], nodata=np.nan)
                    custom_legend_html += f'<div style="display:flex;align-items:center;margin-bottom:6px;"><div style="width:18px;height:18px;background:{c["a_c"]};margin-right:10px;"></div><span style="font-size:14px;color:black;">{name} > {t:.0f} {u_str}</span></div>'
                    has_custom = True
            
            # Continuous or Discrete Multi-Color Mode
            else:
                vmin_val, vmax_val = float(c['vmin']), float(c['vmax'])
                if c.get('sub_mode') == "Multi-Color":
                    if not c.get('ext_min', False): data = data.where(data >= vmin_val, np.nan)
                    if not c.get('ext_max', False): data = data.where(data <= vmax_val, np.nan)
                    cmap_base = plt.get_cmap(c['cmap'])
                    
                    if c.get('disc'): # Discrete Values Processing
                        n = int(c['lv'])
                        bins = np.linspace(vmin_val, vmax_val, n + 1)
                        bin_centers = (bins[:-1] + bins[1:]) / 2
                        idx = np.digitize(data, bins) - 1
                        idx = np.clip(idx, 0, n - 1)
                        data_disc = xr.DataArray(bin_centers[idx], coords=data.coords, dims=data.dims)
                        data_disc = data_disc.where(data.notnull(), np.nan)
                        colors = [mpl.colors.rgb2hex(cmap_base(i)) for i in np.linspace(0, 1, n)]
                        m.add_raster(data_disc, palette=colors, vmin=vmin_val, vmax=vmax_val, layer_name=name, opacity=c['alpha'], nodata=np.nan)
                        m.add_child(cm.StepColormap(colors, vmin=vmin_val, vmax=vmax_val, index=bins, caption=f"{name} {u_str}"))
                    else:
                        colors = [mpl.colors.rgb2hex(cmap_base(i)) for i in np.linspace(0, 1, 256)]
                        m.add_raster(data, palette=colors, vmin=vmin_val, vmax=vmax_val, layer_name=name, opacity=c['alpha'], nodata=np.nan)
                        ticks = np.linspace(vmin_val, vmax_val, 6)
                        cmap_obj = cm.LinearColormap(colors=colors, vmin=vmin_val, vmax=vmax_val, caption=f"{name} {u_str}")
                        cmap_obj = cmap_obj.to_step(index=ticks)
                        m.add_child(cmap_obj)
                else:
                    # Single Color Area Mode
                    data = data.where((data >= vmin_val) & (data <= vmax_val), np.nan)
                    m.add_raster(data, palette=[c['one_c'], c['one_c']], layer_name=name, opacity=c['alpha'], nodata=np.nan)
                    custom_legend_html += f'<div style="display:flex;align-items:center;margin-bottom:6px;"><div style="width:18px;height:18px;background:{c["one_c"]};margin-right:10px;"></div><span style="font-size:14px;color:black;">{name}: {vmin_val:.0f}-{vmax_val:.0f} {u_str}</span></div>'
                    has_custom = True

    # 2. Synthesis Map Logic (Intersecting Multiple Conditions)
    if st.session_state.get('synthesis_active'):
        sel_multi, multi_conf = multi_bundle
        if sel_multi:
            combined_mask = None
            ref_data = layers[sel_multi[0]].copy()
            if 'time' in ref_data.dims: ref_data = ref_data.mean('time')
            if ref_data.rio.crs is None: ref_data.rio.write_crs("EPSG:4326", inplace=True)
            
            synth_rows = ""
            for i, name in enumerate(sel_multi):
                curr = layers[name].copy()
                if 'time' in curr.dims: curr = curr.mean('time')
                if curr.rio.crs is None: curr.rio.write_crs("EPSG:4326", inplace=True)
                
                # Align spatial grids for synthesis calculation
                curr = curr.reindex_like(ref_data, method="nearest")
                
                v_min, v_max = multi_conf['indices'][name]['vmin'], multi_conf['indices'][name]['vmax']
                mask = (curr >= v_min) & (curr.where(curr.notnull()) <= v_max)
                if combined_mask is None: combined_mask = mask
                else: combined_mask = combined_mask & mask
                
                u_str_m = f"({units_dict.get(name, '')})" if units_dict.get(name) else ""
                color_box = f'<div style="width:18px;height:18px;background:{multi_conf["color"]};margin-right:10px;"></div>' if i==0 else '<div style="width:18px;height:18px;margin-right:10px;"></div>'
                synth_rows += f'<div style="display:flex;align-items:center;margin-bottom:4px;">{color_box}<span style="font-size:14px;color:black;">{name}: {v_min:.0f}-{v_max:.0f} {u_str_m}</span></div>'
            
            if combined_mask is not None:
                synth = ref_data.where(combined_mask, np.nan)
                if shp is not None:
                    if synth.rio.crs is None: synth.rio.write_crs("EPSG:4326", inplace=True)
                    synth = synth.rio.clip(shp.geometry, shp.crs, drop=False)
                    synth = synth.where(synth.notnull(), np.nan)
                m.add_raster(synth, palette=[multi_conf['color'], multi_conf['color']], layer_name="Synthesis Map", opacity=multi_conf['alpha'], nodata=np.nan)
                custom_legend_html += f'<div style="margin-top:10px;">{synth_rows}</div>'
                has_custom = True

    # Render fixed-position custom legend if active
    if has_custom:
        legend_div = f'<div style="position:fixed; bottom:35px; right:40px; z-index:9999; background:none; border:none; padding:0; min-width:280px;">{custom_legend_html}</div>'
        m.get_root().html.add_child(folium.Element(legend_div))
    
    m.add_layer_control()
    return m