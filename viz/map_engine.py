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
    """
    Harita katman listesinde görünecek temiz isim.
    """
    clean = file_name.replace(".tif", "").replace("_cog", "")
    parts = clean.split('_')
    
    # Otomatik tespit: Eğer isim çok uzunsa (Future), 11. segmenti al
    if len(parts) > 11:
        found_code = parts[11].upper()
        description = " ".join(parts[12:]).replace("_", " ").title()
    elif len(parts) > 5:
        # Historical tespiti
        found_code = parts[5].upper()
        description = " ".join(parts[6:]).replace("_", " ").title()
    else:
        found_code = "INDEX"
        description = clean.replace("_", " ").title()

    unit_fallback = {"PCD":"Days","SU":"Days","TR":"Days","PRCPTOT":"mm","PET":"mm","UTCI":"°C","DI":"°C"}
    unit = unit_fallback.get(found_code, "")
    
    return f"{prefix}{found_code} - {description}", unit

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
def get_cached_rgba(file_path, vmin, vmax, cmap_input, mode, thresh=None, color_below=None, color_above=None, no_b=False, no_a=False, ext_min=False, ext_max=False):
    data = load_raw_data(file_path) 
    vals = data.values
    mask = ~np.isnan(vals)
    
    # Başlangıçta 4. kanal (Alpha) tamamen 0 (Şeffaf)
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
        # INTERVAL MODU
        if vmin == vmax: vmax += 0.001
        
        # Sadece aralık içindeki pikselleri bul
        valid_range = mask & (vals >= vmin) & (vals <= vmax)
        
        if isinstance(cmap_input, str) and cmap_input.startswith('#'):
            # One-Color Modu
            single_c = mpl.colors.to_rgba(cmap_input)[:3]
            rgba[valid_range, :3] = single_c
            rgba[valid_range, 3] = 1.0
            # Kullanıcı özellikle "altını/üstünü boya" dediyse boya, yoksa şeffaf kalır
            if ext_min: rgba[mask & (vals < vmin), :3] = single_c; rgba[mask & (vals < vmin), 3] = 1.0
            if ext_max: rgba[mask & (vals > vmax), :3] = single_c; rgba[mask & (vals > vmax), 3] = 1.0
        else:
            # Multi-Color (Cmap) Modu
            cmap = plt.get_cmap(cmap_input)
            norm = plt.Normalize(vmin=vmin, vmax=vmax)
            rgba[valid_range, :3] = cmap(norm(vals[valid_range]))[:, :3]
            rgba[valid_range, 3] = 1.0
            if ext_min: rgba[mask & (vals < vmin), :3] = cmap(0.0)[:3]; rgba[mask & (vals < vmin), 3] = 1.0
            if ext_max: rgba[mask & (vals > vmax), :3] = cmap(1.0)[:3]; rgba[mask & (vals > vmax), 3] = 1.0
    
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
                           lcz_bundle=(None, None), lcz_alpha=0.6):

    lcz_leg_final = None
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
    
    .legend:not(:first-of-type) {
        display: none !important;
    }
                                                 
    .legend { 
        margin-top: 10px !important;
        margin-bottom: 40px !important; 
        margin-right: 10px !important; 
        font-size: 16px !important; 
        display: flex !important; 
        flex-direction: column-reverse !important; 
        align-items: center !important; 
        opacity: 1 !important; 
        overflow: visible !important;
        height: auto !important;
        min-height: 90px !important;
        background: rgba(245, 245, 245, 0.95) !important; /* Kırık beyaz/gri */
        border: 1px solid #999 !important;               /* Düz gri çerçeve */
        border-radius: 5px !important;                    /* Yumuşak köşe */
        padding: 15px 12px 10px 12px !important; /* Üst, Sağ, Alt, Sol */
        width: fit-content !important;        /* İçerik kadar genişle (Daraltır) */
        height: auto !important;             /* İçerik kadar boylan */
        box-shadow: none !important;                      /* Gölgeyi kaldırdık */
    }
    
    .legend .caption { 
        font-size: 16px !important; 
        color: #333 !important; 
        margin-bottom: 5px !important; 
        line-height: 1.2 !important; 
        font-weight: bold !important;
        transform: translateY(5px) !important;
        overflow: visible !important;
        color: #333 !important;
        font-family: 'Helvetica Neue', Arial, Helvetica, sans-serif !important;                                         
    }
    
    .legend svg { 
        margin-bottom: 10px !important; 
        opacity: 1 !important; 
        overflow: visible !important;
    }
    
    .legend svg text { 
        fill: #333 !important; 
        font-family: 'Helvetica Neue', Arial, Helvetica, sans-serif !important;
        font-weight: bold !important; 
        font-size: 14px !important; 
    }
    
    .leaflet-top.leaflet-right { 
        display: flex !important; 
        flex-direction: column !important; 
        align-items: flex-end !important; 
        gap: 30px !important; 
        top: 0px !important;    /* Değer küçüldükçe yukarı  */
    }
    </style>
    """))
    
    # --- 1. LİSTEDE EN ÜST / GÖRSELDE EN ALT: OSM ---
    if show_osm:
        folium.TileLayer(
            tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='&copy; OSM', name='Open Street Map', overlay=True, control=True
        ).add_to(m)

    # --- 2. LİSTEDE 2. SIRADA: LCZ ---
    lcz_b64, lcz_bounds = lcz_bundle

    # Lejant HTML (NameError engellemek için fonksiyon içinde de tanımlı)
    lcz_leg_final = """
        <div style="position: fixed; bottom: 40px; left: 5px; width: 210px; z-index:9999; 
            background-color: rgba(255, 255, 255, 0.95); padding: 8px; border: 1px solid #999; 
            border-radius: 5px; font-size: 11px; font-family: 'Helvetica Neue', Arial, Helvetica, sans-serif; color: #333;
            box-shadow: none;">
    <b style="font-size:12px; display:block; margin-bottom:5px; border-bottom:1px solid #ddd;">Local Climate Zones</b>
    <div style="display: flex; gap: 4px;">
        <div style="flex: 1;">
                    <b>Built</b><br>
                    <i style="background:#990000;width:9px;height:9px;display:inline-block"></i> 1 Comp. High<br>
                    <i style="background:#e40000;width:9px;height:9px;display:inline-block"></i> 2 Comp. Mid<br>
                    <i style="background:#ff0000;width:9px;height:9px;display:inline-block"></i> 3 Comp. Low<br>
                    <i style="background:#ce4400;width:9px;height:9px;display:inline-block"></i> 4 Open High<br>
                    <i style="background:#ff5900;width:9px;height:9px;display:inline-block"></i> 5 Open Mid<br>
                    <i style="background:#ff9442;width:9px;height:9px;display:inline-block"></i> 6 Open Low<br>
                    <i style="background:#fcef00;width:9px;height:9px;display:inline-block"></i> 7 Light Low<br>
                    <i style="background:#bcbcbc;width:9px;height:9px;display:inline-block"></i> 8 Large Low<br>
                    <i style="background:#ffcaa5;width:9px;height:9px;display:inline-block"></i> 9 Sparsely<br>
                    <i style="background:#555555;width:9px;height:9px;display:inline-block"></i> 10 Industry
                </div>
                <div style="flex: 1;">
                    <b>Land Cover</b><br>
                    <i style="background:#006d00;width:9px;height:9px;display:inline-block"></i> A Dense Trees<br>
                    <i style="background:#00ae00;width:9px;height:9px;display:inline-block"></i> B Scattered<br>
                    <i style="background:#5a8700;width:9px;height:9px;display:inline-block"></i> C Bush/Scrub<br>
                    <i style="background:#b0dd6a;width:9px;height:9px;display:inline-block"></i> D Low Plants<br>
                    <i style="background:#000000;width:9px;height:9px;display:inline-block"></i> E Bare Rock<br>
                    <i style="background:#fbf7ae;width:9px;height:9px;display:inline-block"></i> F Bare Soil<br>
                    <i style="background:#6a6aff;width:9px;height:9px;display:inline-block"></i> G Water
                </div>
            </div>
        </div>
        """
    
    if lcz_b64:
        folium.raster_layers.ImageOverlay(
            image=lcz_b64, bounds=lcz_bounds, opacity=lcz_alpha,
            name="Local Climate Zones", zindex=4
        ).add_to(m)
        m.get_root().html.add_child(folium.Element(lcz_leg_final))

        if lcz_leg_final:  # Sadece içi doluysa haritaya ekle
            m.get_root().html.add_child(folium.Element(lcz_leg_final))

    # --- 3. LİSTEDE 3. SIRADA: İLLER ---
    if show_provinces and shp is not None:
        temp_shp = shp[['Şehir', 'geometry']].copy() if 'Şehir' in shp.columns else shp[['ADM1_TR', 'geometry']].copy()
        temp_shp.columns = ['Şehir', 'geometry']
        m.add_gdf(temp_shp, layer_name="Türkiye Provinces", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.2}, labels=False)

    # --- 4. LİSTEDE 4. SIRADA / GÖRSELDE EN ÜSTTE: İLÇELER ---
    if show_districts and districts_shp is not None:
        temp_dist = districts_shp[['Şehir', 'İlçe', 'geometry']].copy() if 'Şehir' in districts_shp.columns else districts_shp[['ADM1_TR', 'ADM2_TR', 'geometry']].copy()
        temp_dist.columns = ['Şehir', 'İlçe', 'geometry']
        temp_dist.loc[temp_dist['Şehir'] == temp_dist['İlçe'], 'İlçe'] = temp_dist['İlçe'] + " (Merkez)"
        # zindex kullanmadan bile en son eklediğimiz için en üstte (fareyle dokunulabilir) kalacak
        m.add_gdf(temp_dist, layer_name="Türkiye Districts", style={'color': '#444444', 'fillOpacity': 0, 'weight': 0.2}, labels=False, zoom_to_layer=False)
        

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
                c.get('vmin', 0.0), 
                c.get('vmax', 1.0), 
                (c.get('one_c', '#DC7933') if c.get('sub_mode') == "One-Color" else c.get('cmap', 'viridis')), 
                c['mode'], 
                c.get('thresh'), 
                c.get('b_c'), 
                c.get('a_c'), 
                c.get('b_m') == "No Color", 
                c.get('a_m') == "No Color",
                c.get('ext_min', False), # False yaptık
                c.get('ext_max', False)  # False yaptık
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
        m.get_root().html.add_child(folium.Element(f'''
            <div style="position:fixed; bottom:40px; 
            right:10px; z-index:9999; 
            background:rgba(255,255,255,0.95); 
            padding:15px; border-radius:5px; 
            border:1px solid #999; 
            box-shadow: none; 
            min-width:240px;
            font-family: 'Helvetica Neue', Arial, Helvetica, sans-serif; color: #333;">
            {custom_legend_html}
            </div>
        '''))
    
    m.add_layer_control()
    return m