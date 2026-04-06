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
<div style="position: fixed; bottom: 80px; left: 20px; width: 180px; z-index:9999; 
            background-color: rgba(255, 255, 255, 0.95); padding: 8px; border: 1px solid #888; 
            border-radius: 5px; font-size: 10.5px; font-family: 'Arial Narrow'; color: black;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.2);">
    <b style="font-size:12px; display:block; margin-bottom:5px; border-bottom:1px solid #ccc;">Local Climate Zones</b>
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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- 1. SESSION STATE ---
for key, val in [('map_center', [38.9, 35.5]), ('map_zoom', 5), ('map_rendered', False), ('map_trigger', 0), 
                 ('applied_sel_one', []), ('applied_one_conf', {}), ('applied_multi_bundle', ([], {}))]:
    if key not in st.session_state: st.session_state[key] = val

# --- CSS (Genel Görsel Ayarlar) ---
st.markdown("<style>.main .block-container { padding-top: 5rem !important; } footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# --- 2. VERİ ÖN YÜKLEME ---
shp = load_turkiye_shp()
districts_shp = load_districts_shp() # İlçeleri yükle

# A. Historical Veriler {Friendly_Name: Filename}
av_dict_hist = list_available_indices()
stats_hist = load_stats()

# B. Future (SSP245) Verileri {Filename: Filename}
# ÖNEMLİ: Anahtarı dosya adı yaptık ki farklı dönemlerdeki aynı isimli indisler birbirini silmesin.
future_files = glob.glob(os.path.join(FUTURE_SSP245_DIR, "*.tif"))
av_dict_future = {os.path.basename(f): os.path.basename(f) for f in future_files}

with open(FUTURE_SSP245_STATS, 'r') as f:
    stats_future = json.load(f)

# C. MAP ENGINE İÇİN YOL SÖZLÜĞÜ: {Filename: Full_Path}
engine_path_map = {
    **{f: os.path.join(INDICES_DIR, f) for f in av_dict_hist.values()}, # Historical
    **{os.path.basename(f): f for f in future_files}                   # Future
}

# D. Tüm istatistikleri birleştir {Filename: Stats}
total_stats = {**stats_hist, **stats_future}

# --- 3. SIDEBAR RENDER ---
one_bundle, multi_bundle = render_sidebar(
    av_dict_hist, 
    av_dict_future, 
    {}, # units_dict_hist
    {}, # units_dict_future
    stats_hist, 
    stats_future
)

with st.sidebar:
    st.subheader("Layers")
    show_provinces = st.toggle("Provinces", value=True, key="show_provinces")
    show_districts = st.toggle("Districts", value=True, key="show_districts")
    show_osm = st.toggle("Open Street Map", value=True, key="show_osm") 
    show_lcz = st.toggle("Local Climate Zones", value=False, key="show_lcz")
    lcz_alpha = 0.6 # Varsayılan
    if show_lcz:
        lcz_alpha = st.slider("LCZ Opacity", 0.0, 1.0, 0.6, key="lcz_alpha")
    st.markdown("---")

lcz_bundle = load_lcz_static() if show_lcz else (None, None)

# --- UPDATE MAP BUTONU ---
with st.sidebar:
    st.markdown("---")
    if st.button("Update Map", use_container_width=True, type="primary"):
        st.session_state.applied_one_conf = one_bundle[1].copy()
        st.session_state.applied_sel_one = one_bundle[0].copy()
        st.session_state.applied_multi_bundle = multi_bundle if multi_bundle[0] else ([], {})
        st.session_state.synthesis_active = bool(multi_bundle[0])
        st.session_state.map_trigger += 1 
        st.session_state.map_rendered = True
        st.rerun()

# --- 4. HARİTA BÖLÜMÜ (FRAGMENT) ---
@st.fragment
def render_isolated_map_section(trigger, show_provinces, show_districts, show_osm, lcz_bundle, lcz_alpha):
    if st.session_state.map_rendered:
        sel = st.session_state.applied_sel_one
        conf = st.session_state.applied_one_conf
        multi = st.session_state.applied_multi_bundle
        units_data = {k: total_stats.get(k, {}).get('unit', '') for k in list(set(sel) | set(multi[0]))}

        m = create_interactive_map(
            shp, districts_shp, (sel, conf), multi, units_data, 
            engine_path_map, show_provinces, show_districts, show_osm, 
            lcz_bundle, lcz_alpha # lcz_alpha'yı buraya da ekledik
        )
        m.to_streamlit(height=1200, key="main_map_stable_key")

    else:
        m = leafmap.Map(center=[38.9, 35.5], zoom=5, tiles=None)
        
        # --- LCZ (Else bloğu - Anlık tepki) ---
        lcz_b64, lcz_bounds = lcz_bundle
        if show_lcz and lcz_b64:
            folium.raster_layers.ImageOverlay(
                image=lcz_b64, bounds=lcz_bounds, opacity=lcz_alpha,
                name="Local Climate Zones", zindex=4
            ).add_to(m)
            # Demin geliyordu dediğin yöntem (html.add_child)
            m.get_root().html.add_child(folium.Element(LCZ_LEGEND_HTML))

        # --- DİĞER KATMANLAR (OSM, Provinces, districts) ---
        if show_osm:
            folium.TileLayer(tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', attr='&copy; OSM', name='Open Street Map', overlay=True).add_to(m)
        if show_provinces and shp is not None:
            m.add_gdf(shp[['ADM1_TR', 'geometry']].copy(), layer_name="Türkiye Provinces", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.2})
        if show_districts and districts_shp is not None:
            m.add_gdf(districts_shp[['ADM1_TR', 'ADM2_TR', 'geometry']].copy(), layer_name="Türkiye Districts", style={'color': '#444444', 'fillOpacity': 0, 'weight': 0.2})
            
        m.to_streamlit(height=1200, key="stable_map_render")

render_isolated_map_section(st.session_state.map_trigger, show_provinces, show_districts, show_osm, lcz_bundle, lcz_alpha)