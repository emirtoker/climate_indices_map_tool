import sys, os
import streamlit as st
import json
import glob
import folium

# --- KRİTİK: PATH AYARI EN ÜSTTE OLMALI ---
# Bu satır, Python'un 'core', 'viz', 'app' klasörlerini görmesini sağlar.
current_dir = os.path.dirname(os.path.abspath(__file__)) # app klasörü
project_root = os.path.dirname(current_dir) # Proje ana dizini
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- ŞİMDİ KENDİ MODÜLLERİNİ ÇAĞIRABİLİRSİN ---
from core.data_loader import load_turkiye_shp, load_districts_shp, list_available_indices, load_stats, load_lcz_static
from app.sidebar import render_sidebar, get_clean_name_logic
from viz.map_engine import create_interactive_map



from core.data_loader import load_turkiye_shp, load_districts_shp, list_available_indices, load_stats
from app.sidebar import render_sidebar, get_clean_name_logic
from viz.map_engine import create_interactive_map
import leafmap.foliumap as leafmap
from config.settings import FUTURE_SSP245_DIR, FUTURE_SSP245_STATS, INDICES_DIR
from core.data_loader import load_lcz_data
from core.data_loader import load_lcz_static


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
    show_lcz = st.toggle("Local Climate Zones", value=False)
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
def render_isolated_map_section(trigger, show_provinces, show_districts, show_osm, lcz_bundle):
    if st.session_state.map_rendered:
        sel = st.session_state.applied_sel_one
        conf = st.session_state.applied_one_conf
        multi = st.session_state.applied_multi_bundle
        units_data = {k: total_stats.get(k, {}).get('unit', '') for k in list(set(sel) | set(multi[0]))}

        m = create_interactive_map(shp, districts_shp, (sel, conf), multi, units_data, engine_path_map, show_provinces, show_districts, show_osm, lcz_bundle)
        m.to_streamlit(height=1200, key="main_map_stable_key")

    else:
        # 1. Haritayı oluştur 
        m = leafmap.Map(center=[38.9, 35.5], zoom=5, tiles=None)
        
        # --- LCZ (Başlangıçta da görünsün istenirse) ---
        lcz_b64, lcz_bounds = lcz_bundle
        if lcz_b64:
            folium.raster_layers.ImageOverlay(
                image=lcz_b64,
                bounds=lcz_bounds,
                opacity=0.6,
                name="Local Climate Zones (LCZ)",
                zindex=4
            ).add_to(m)

        # --- A. OSM ---
        if show_osm:
            folium.TileLayer(
                tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                attr='&copy; OpenStreetMap contributors',
                name='OpenStreetMap',
                overlay=True,
                control=True
            ).add_to(m)

        # --- B. ORTA: İLLER (Provinces) ---
        if show_provinces and shp is not None:
            temp_shp = shp[['ADM1_TR', 'geometry']].copy()
            temp_shp.columns = ['Şehir', 'geometry']
            m.add_gdf(
                temp_shp, 
                layer_name="Türkiye Provinces", 
                style={'color': 'black', 'fillOpacity': 0, 'weight': 1.2} # Çizgiyi azıcık kalınlaştırdım
            )

        # --- C. EN ÜST: İLÇELER (Districts) ---
        if show_districts and districts_shp is not None:
            temp_dist = districts_shp[['ADM1_TR', 'ADM2_TR', 'geometry']].copy()
            temp_dist.columns = ['Şehir', 'İlçe', 'geometry']
            temp_dist.loc[temp_dist['Şehir'] == temp_dist['İlçe'], 'İlçe'] = temp_dist['İlçe'] + " (Merkez)"
            
            m.add_gdf(
                temp_dist, 
                layer_name="Türkiye Districts", 
                style={'color': '#444444', 'fillOpacity': 0, 'weight': 0.2}
            )
            
        m.to_streamlit(height=1200, key="stable_map_render")

render_isolated_map_section(st.session_state.map_trigger, show_provinces, show_districts, show_osm, lcz_bundle)