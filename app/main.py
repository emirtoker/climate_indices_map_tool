import sys, os
import streamlit as st
import json
import glob
import folium
import leafmap.foliumap as leafmap

# --- PATH AYARI ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.data_loader import load_turkiye_shp, load_districts_shp, list_available_indices, load_stats, load_lcz_static
from app.sidebar import render_sidebar
from viz.map_engine import create_interactive_map
from config.settings import FUTURE_SSP245_DIR, FUTURE_SSP245_STATS, INDICES_DIR

# --- LCZ LEJANT METNİ ---
LCZ_LEGEND_HTML = """
<div style="position: fixed; bottom: 40px; left: 5px; width: 210px; z-index:9999; 
            background-color: rgba(255, 255, 255, 0.95); padding: 8px; border: 1px solid #999; 
            border-radius: 5px; font-size: 11px; font-family: 'Helvetica Neue', Arial, Helvetica, sans-serif; color: #333;
            box-shadow: none;">
    <b style="font-size:12px; display:block; margin-bottom:5px; border-bottom:1px solid #ddd;">Local Climate Zones</b>
    <div style="display: flex; gap: 4px;">
        <div style="flex: 1;">
            <b style="color:#555;">Built</b><br>
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
            <b style="color:#555;">Land Cover</b><br>
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


# Sayfa konfigürasyonu
st.set_page_config(page_title="Indices Map Tool", layout="wide")

# --- 1. SESSION STATE ---
init_vals = [
    ('map_center', [38.9, 35.5]), ('map_zoom', 5), ('map_rendered', False), ('map_trigger', 0), 
    ('applied_sel_one', []), ('applied_one_conf', {}), ('applied_multi_bundle', ([], {})),
    ('app_show_provinces', True), ('app_show_districts', True), ('app_show_osm', True),
    ('app_show_lcz', True), ('app_lcz_alpha', 0.4),
    ('ui_provinces', True), ('ui_districts', True), ('ui_osm', True), 
    ('ui_lcz', True), ('ui_alpha', 0.4)
]
for key, val in init_vals:
    if key not in st.session_state: st.session_state[key] = val

# --- CSS (Genel Görsel Ayarlar) ---
st.markdown("<style>.main .block-container { padding-top: 5rem !important; } footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# --- 2. VERİ ÖN YÜKLEME ---
shp = load_turkiye_shp()
districts_shp = load_districts_shp() # İlçeleri yükle

# A. Historical Veriler
av_dict_hist = list_available_indices()
stats_hist = load_stats(mode="historical")

# B. Future (SSP245) Verileri
if os.path.exists(FUTURE_SSP245_DIR):
    future_files = glob.glob(os.path.join(FUTURE_SSP245_DIR, "*.tif"))
    # stats.json'ı listeden çıkar
    future_files = [f for f in future_files if "stats.json" not in f]
    av_dict_future = {os.path.basename(f): os.path.basename(f) for f in future_files}
    stats_future = load_stats(mode="future")
else:
    av_dict_future = {}
    stats_future = {}

# C. MAP ENGINE İÇİN YOL SÖZLÜĞÜ
engine_path_map = {
    **{f: os.path.join(INDICES_DIR, f) for f in av_dict_hist.values()},
    **{os.path.basename(f): f for f in future_files}
}

# D. Tüm istatistikleri birleştir
total_stats = {**stats_hist, **stats_future}

# --- 3. SIDEBAR RENDER ---
one_bundle, multi_bundle = render_sidebar(
    av_dict_hist, av_dict_future, {}, {}, stats_hist, stats_future
)

@st.fragment
def render_reference_layers_ui():
    with st.container(border=True):
        st.subheader("Reference Layers")
        # 1. Open Street Map (En Üstte)
        st.checkbox("Open Street Map", key="ui_osm")
        
        # 2. Local Climate Zones + Opacity hemen altında
        show_lcz = st.checkbox("Local Climate Zones", key="ui_lcz")
        if show_lcz:
            st.slider("LCZ Opacity", 0.0, 1.0, step=0.05, key="ui_alpha")
        
        # 3. İller ve İlçeler
        st.checkbox("Türkiye Provinces", key="ui_provinces")
        st.checkbox("Türkiye Districts", key="ui_districts")
    

# --- 1. REFERENCE LAYERS (Anlık UI, Donmuş Harita) ---
with st.sidebar:
    # 1. Referans katmanların "izole" kutusunu çağırıyoruz
    render_reference_layers_ui()
    
    st.markdown("---")

    # 2. UPDATE MAP (Tüm sayfayı ve haritayı tetikler)
    if st.button("Update Map", use_container_width=True, type="primary"):
        st.session_state.applied_one_conf = one_bundle[1].copy()
        st.session_state.applied_sel_one = one_bundle[0].copy()
        st.session_state.applied_multi_bundle = multi_bundle if multi_bundle[0] else ([], {})
        st.session_state.synthesis_active = bool(multi_bundle[0])
        st.session_state.app_show_provinces = st.session_state.ui_provinces
        st.session_state.app_show_districts = st.session_state.ui_districts
        st.session_state.app_show_osm = st.session_state.ui_osm
        st.session_state.app_show_lcz = st.session_state.ui_lcz
        st.session_state.app_lcz_alpha = st.session_state.ui_alpha
        
        st.session_state.map_trigger += 1 
        st.session_state.map_rendered = True
        st.rerun()

    # 3. RESET MAP
    if st.button("Reset Map", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            if key not in ['map_center', 'map_zoom']:
                del st.session_state[key]
        st.session_state.map_rendered = False
        st.rerun()


# --- 4. HARİTA BÖLÜMÜ (FRAGMENT) ---
@st.fragment
def render_isolated_map_section(trigger):
    # Kilitlenmiş değerleri çek
    show_p = st.session_state.app_show_provinces
    show_d = st.session_state.app_show_districts
    show_o = st.session_state.app_show_osm
    show_l = st.session_state.app_show_lcz
    alpha_l = st.session_state.app_lcz_alpha
    
    # LCZ yüklemesi de butonu bekler
    lcz_bundle = load_lcz_static() if show_l else (None, None)

    if st.session_state.map_rendered:
        sel = st.session_state.applied_sel_one
        conf = st.session_state.applied_one_conf
        multi = st.session_state.applied_multi_bundle
        units_data = {k: total_stats.get(k, {}).get('unit', '') for k in list(set(sel) | set(multi[0]))}

        m = create_interactive_map(
            shp, districts_shp, (sel, conf), multi, units_data, 
            engine_path_map, show_p, show_d, show_o, lcz_bundle, alpha_l
        )
        m.to_streamlit(height=1200, key="main_map_stable_key")

    else:
        m = leafmap.Map(center=[38.9, 35.5], zoom=5, tiles=None)
        
        # SIRA: OSM -> LCZ -> İl -> İlçe (Bu sıra hem listeyi hem görseli ayarlar)
        if show_o:
            folium.TileLayer(tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', attr='&copy; OSM', name='Open Street Map', overlay=True).add_to(m)
        
        if show_l and lcz_bundle[0]:
            folium.raster_layers.ImageOverlay(image=lcz_bundle[0], bounds=lcz_bundle[1], opacity=alpha_l, name="Local Climate Zones", zindex=4).add_to(m)
            m.get_root().html.add_child(folium.Element(LCZ_LEGEND_HTML))

        if show_p and shp is not None:
            temp_shp = shp[['ADM1_TR', 'geometry']].copy(); temp_shp.columns = ['Şehir', 'geometry']
            m.add_gdf(temp_shp, layer_name="Türkiye Provinces", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.2})

        if show_d and districts_shp is not None:
            temp_dist = districts_shp[['ADM1_TR', 'ADM2_TR', 'geometry']].copy(); temp_dist.columns = ['Şehir', 'İlçe', 'geometry']
            temp_dist.loc[temp_dist['Şehir'] == temp_dist['İlçe'], 'İlçe'] = temp_dist['İlçe'] + " (Merkez)"
            m.add_gdf(temp_dist, layer_name="Türkiye Districts", style={'color': '#444444', 'fillOpacity': 0, 'weight': 0.2})
            
        m.to_streamlit(height=1200, key="stable_map_render")

render_isolated_map_section(st.session_state.map_trigger)