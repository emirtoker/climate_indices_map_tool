import os
import streamlit as st
import leafmap.foliumap as leafmap
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import branca.colormap as cm
import folium  # En üstte olduğundan emin ol
from folium.raster_layers import ImageOverlay 
from PIL import Image
import io
import base64


def get_clean_label(file_name, prefix=""):
    codes = ["PCD", "PRCPTOT", "SU", "TR", "DI", "HI", "PET", "SPI", "SPEI", "UTCI"]
    unit_fallback = {"PCD":"Days","SU":"Days","TR":"Days","PRCPTOT":"mm","PET":"mm","UTCI":"°C","DI":"°C","HI":"°C","SPI":"Index","SPEI":"Index"}
    clean = file_name.replace(".tif", "").replace("_cog", "")
    parts = clean.split('_')
    found_code, found_idx = None, -1
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].upper() in codes:
            if parts[i].upper() == "TR" and i < 4: continue
            found_code, found_idx = parts[i].upper(), i
            break
    if found_code:
        description = " ".join(parts[found_idx + 1:]).replace("_", " ").title()
        label = f"{found_code} - {description}"
        unit = unit_fallback.get(found_code, "")
    else:
        label, unit = clean.replace("_", " ").title(), ""
    return f"{prefix}{label}", unit

# --- AŞAMA 1: AKILLI COG OKUMA (OVERVIEWS DESTEKLİ) ---
@st.cache_data(show_spinner=False, max_entries=5)
def load_raw_data(file_name, max_width=1200):
    import rioxarray
    # Doğrudan rioxarray ile açarak overview'lardan faydalanıyoruz
    # Bu sayede koca dosyayı değil, ihtiyacımız olan çözünürlüğü okuyoruz
    ds = rioxarray.open_rasterio(file_name, mask_and_scale=True)
    
    # Eğer veri çok büyükse, en yakın overview seviyesine küçült (Decimation)
    # Bu işlem COG olduğu için milisaniyeler sürer
    if ds.rio.width > max_width:
        scale_factor = max_width / ds.rio.width
        new_width = int(ds.rio.width * scale_factor)
        new_height = int(ds.rio.height * scale_factor)
        # out_shape kullanımı COG içindeki piramitleri (overviews) otomatik seçer
        ds = ds.rio.reproject(ds.rio.crs, shape=(new_height, new_width))
        
    if 'time' in ds.dims: ds = ds.mean(dim='time')
    if 'band' in ds.dims: ds = ds.sel(band=1)
        
    return ds

# --- AŞAMA 2: HIZLI PNG ENCODE ---
@st.cache_data(show_spinner=False, max_entries=10)
def rgba_to_png_base64(rgba_uint8):
    img = Image.fromarray(rgba_uint8)
    buf = io.BytesIO()
    # 'optimize=True' kısmını kaldırdık, CPU yerine ağ hızına odaklandık
    # PNG yerine bazen WebP denenebilir ama uyumluluk için PNG iyidir
    img.save(buf, format="PNG", compress_level=3) # 1-9 arası; 3 hız/boyut dengesidir
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

# --- AŞAMA 3: AKILLI RENKLENDİRME ---
@st.cache_data(show_spinner=False, max_entries=5)
def get_cached_rgba(file_path, vmin, vmax, cmap_input, mode, thresh=None, color_below=None, color_above=None, no_b=False, no_a=False, ext_min=True, ext_max=True):
    # Artık dosya yolunu (full_path) gönderiyoruz
    data = load_raw_data(file_path) 
    vals = data.values
    mask = ~np.isnan(vals)
    
    # Bellek tasarrufu için float32 yerine uint8'e hazırlık yapıyoruz
    rgba = np.zeros((*vals.shape, 4), dtype=np.float32)

    if mode == "Threshold":
        t = thresh
        if not no_b: 
            idx = mask & (vals < t)
            rgba[idx, :3] = mpl.colors.to_rgba(color_below)[:3]
            rgba[idx, 3] = 1.0
        if not no_a: 
            idx = mask & (vals > t)
            rgba[idx, :3] = mpl.colors.to_rgba(color_above)[:3]
            rgba[idx, 3] = 1.0
    else:
        if vmin == vmax: vmax += 0.001
        if isinstance(cmap_input, str) and cmap_input.startswith('#'):
            single_c = mpl.colors.to_rgba(cmap_input)[:3]
            valid = mask & (vals >= vmin) & (vals <= vmax)
            rgba[valid, :3] = single_c
            rgba[valid, 3] = 1.0
            if ext_min: rgba[mask & (vals < vmin), :3] = single_c; rgba[mask & (vals < vmin), 3] = 1.0
            if ext_max: rgba[mask & (vals > vmax), :3] = single_c; rgba[mask & (vals > vmax), 3] = 1.0
        else:
            cmap = plt.get_cmap(cmap_input)
            norm = plt.Normalize(vmin=vmin, vmax=vmax)
            valid = mask & (vals >= vmin) & (vals <= vmax)
            # Matplotlib'in vektörize gücünü kullanıyoruz
            rgba[valid, :3] = cmap(norm(vals[valid]))[:, :3]
            rgba[valid, 3] = 1.0
            if ext_min: rgba[mask & (vals < vmin), :3] = cmap(0.0)[:3]; rgba[mask & (vals < vmin), 3] = 1.0
            if ext_max: rgba[mask & (vals > vmax), :3] = cmap(1.0)[:3]; rgba[mask & (vals > vmax), 3] = 1.0
    
    # Koordinat sınırlarını al
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

def create_interactive_map(shp, districts_shp, one_bundle, multi_bundle, units_dict, available_dict, 
                           show_provinces=True, show_districts=True, show_osm=True, 
                           lcz_bundle=(None, None)):

    # Haritayı oluştur
    m = leafmap.Map(
        center=st.session_state.get('map_center', [38.9, 35.5]), 
        zoom=st.session_state.get('map_zoom', 5), 
        tiles=None, 
        control_scale=True
    )

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
        transform: translateY(5px) !important;
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
    
    # --- 1. EN ALT: OSM ---
    if show_osm:
        folium.TileLayer(
            tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='&copy; OpenStreetMap contributors',
            name='OpenStreetMap',
            overlay=True,
            control=True
        ).add_to(m)

    # --- 2. ORTA: İLLER ---
    if show_provinces and shp is not None:
        temp_shp = shp[['Şehir', 'geometry']].copy() if 'Şehir' in shp.columns else shp[['ADM1_TR', 'geometry']].copy()
        temp_shp.columns = ['Şehir', 'geometry']
        m.add_gdf(temp_shp, layer_name="Türkiye Provinces", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.2}, labels=False)

    # --- 3. EN ÜST: İLÇELER ---
    if show_districts and districts_shp is not None:
        temp_dist = districts_shp[['Şehir', 'İlçe', 'geometry']].copy() if 'Şehir' in districts_shp.columns else districts_shp[['ADM1_TR', 'ADM2_TR', 'geometry']].copy()
        temp_dist.columns = ['Şehir', 'İlçe', 'geometry']
        temp_dist.loc[temp_dist['Şehir'] == temp_dist['İlçe'], 'İlçe'] = temp_dist['İlçe'] + " (Merkez)"
        m.add_gdf(temp_dist, layer_name="Türkiye Districts", style={'color': '#444444', 'fillOpacity': 0, 'weight': 0.2}, labels=False, zoom_to_layer=False)

    # --- 4. LCZ KATMANI ---
    lcz_b64, lcz_bounds = lcz_bundle
    if lcz_b64:
        folium.raster_layers.ImageOverlay(
            image=lcz_b64,
            bounds=lcz_bounds,
            opacity=0.6,
            name="Local Climate Zones (LCZ)",
            zindex=4
        ).add_to(m)

    custom_legend_html = ""; has_custom = False

    # --- 1. SINGLE INDICE ---
    if one_bundle:
        sel_one, one_conf = one_bundle
        for name in sel_one:
            if name not in available_dict: continue
            c = one_conf[name]
            if not c.get('visible', True): continue
            
            # Veriyi renklendir (Anahtarları .get() ile güvenli okuyoruz)
            rgba, bnds = get_cached_rgba(
                available_dict[name], 
                c.get('vmin', 0.0), # Değişen yer 1: KeyError engellendi
                c.get('vmax', 1.0), # Değişen yer 2: KeyError engellendi
                (c.get('one_c', '#DC7933') if c.get('sub_mode') == "One-Color" else c.get('cmap', 'viridis')), 
                c['mode'], 
                c.get('thresh'), 
                c.get('b_c'), 
                c.get('a_c'), 
                c.get('b_m') == "No Color", 
                c.get('a_m') == "No Color",
                c.get('ext_min', True), 
                c.get('ext_max', True)
            )

            # Başlık Hazırla
            prefix = c.get('legend_prefix', "")
            clean_name, fb_unit = get_clean_label(name, prefix) 

            ImageOverlay(
                image=rgba_to_png_base64(rgba), 
                bounds=bnds, 
                opacity=c['alpha'], 
                name=clean_name, # Artık layer panelinde temiz isim görünecek
                zindex=5
            ).add_to(m)
            
            # Başlık Hazırla
            json_unit = units_dict.get(name, "")
            unit = json_unit if json_unit else fb_unit
            colorbar_title = f"{clean_name} ({unit})" if unit else clean_name
            
            if c['mode'] == "Interval" and c.get('sub_mode') == "Multi-Color":
                n_lv = int(c.get('lv', 10))
                bins = [float(x) for x in np.linspace(c['vmin'], c['vmax'], n_lv + 1)]
                colors = [mpl.colors.rgb2hex(plt.get_cmap(c['cmap'])(i)) for i in np.linspace(0, 1, n_lv)]
                step_cm = cm.StepColormap(colors, vmin=bins[0], vmax=bins[-1], index=bins, caption=colorbar_title)
                step_cm.tick_labels = bins # 0'ı silecek olan vuruş bu!
                m.add_child(step_cm)
                
            elif c['mode'] == "Interval":
                # Tek renkli lejant kutusu (Boyut 20px, border 1px siyah yapıldı)
                line = '<div style="border-top:1px solid #ccc; margin:8px 0;"></div>' if custom_legend_html else ""
                custom_legend_html += f'{line}<div style="display:flex;align-items:center;margin-bottom:8px;"><div style="width:20px;height:20px;background:{c["one_c"]};margin-right:10px; border:1px solid black;"></div><span style="color:black; font-size:15px; font-weight:bold;">{clean_name}: {c["vmin"]:.0f}-{c["vmax"]:.0f}</span></div>'
                has_custom = True

            elif c['mode'] == "Threshold":
                line = '<div style="border-top:1px solid #ccc; margin:8px 0;"></div>' if custom_legend_html else ""
                thresh_val = c.get('thresh', 0.0)
                unit_str = f" {unit}" if unit else ""
                
                rows = ""
                # Lower (Boyut 20px, border 1px siyah yapıldı)
                if c.get('b_m') != "No Color":
                    rows += f'''
                    <div style="display:flex;align-items:center;margin-bottom:4px;">
                        <div style="width:20px;height:20px;background:{c.get('b_c', '#4747B5')};margin-right:10px; border:1px solid black;"></div>
                        <span style="color:black; font-size:14px; font-weight:bold;">{clean_name} < {thresh_val:.1f}{unit_str}</span>
                    </div>'''
                
                # Higher (Boyut 20px, border 1px siyah yapıldı)
                if c.get('a_m') != "No Color":
                    rows += f'''
                    <div style="display:flex;align-items:center;margin-bottom:4px;">
                        <div style="width:20px;height:20px;background:{c.get('a_c', '#C93131')};margin-right:10px; border:1px solid black;"></div>
                        <span style="color:black; font-size:14px; font-weight:bold;">{clean_name} > {thresh_val:.1f}{unit_str}</span>
                    </div>'''
                
                if rows:
                    custom_legend_html += f'{line}{rows}'
                    has_custom = True

    # --- 2. MULTI INDICES ---
    if st.session_state.get('synthesis_active') and multi_bundle[0]:
        sel_multi, multi_conf = multi_bundle
        s_rgba, bnds = get_synthesis_rgba(tuple([available_dict[n] for n in sel_multi]), tuple([multi_conf['indices'][n]['vmin'] for n in sel_multi]), tuple([multi_conf['indices'][n]['vmax'] for n in sel_multi]), multi_conf['color'])
        if s_rgba is not None:
            ImageOverlay(
                image=rgba_to_png_base64(s_rgba), 
                bounds=bnds, 
                opacity=multi_conf['alpha'], 
                name="Synthesis Map", 
                zindex=6
            ).add_to(m)
            
            # AYAR: Çizgi marjı 8px yapıldı ve padding-top (fazla boşluk) kaldırıldı
            if custom_legend_html: 
                custom_legend_html += '<div style="border-top:1px solid #ccc; margin:8px 0;"></div>'
            
            synth_rows = ""
            for i, name in enumerate(sel_multi):
                display_name = multi_conf['indices'][name].get('legend_name', get_clean_label(name))
                v_min_m = multi_conf['indices'][name]['vmin']
                v_max_m = multi_conf['indices'][name]['vmax']
                color_box = multi_conf["color"] if i == 0 else "transparent"
                border = "1px solid black" if i == 0 else "none"
                
                # Alt boşluk (margin-bottom) 6px yapılarak diğer modlarla dengelendi
                synth_rows += f'''
                <div style="display:flex;align-items:center;margin-bottom:6px;">
                    <div style="width:20px;height:20px;background:{color_box};margin-right:10px; border:{border};"></div>
                    <span style="color:black; font-size:15px; font-weight:bold;">{display_name}: {v_min_m:.0f}-{v_max_m:.0f}</span>
                </div>'''
            
            custom_legend_html += f'<div>{synth_rows}</div>'
            has_custom = True

    if has_custom:
        m.get_root().html.add_child(folium.Element(f'<div style="position:fixed; bottom:40px; right:40px; z-index:9999; background:rgba(255,255,255,0.95); padding:15px; border-radius:10px; border:2px solid #333; box-shadow: 5px 5px 15px rgba(0,0,0,0.3); min-width:240px;">{custom_legend_html}</div>'))
    
    m.add_layer_control()
    return m