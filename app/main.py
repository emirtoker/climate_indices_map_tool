import sys, os
import streamlit as st
import json
import glob

# Sayfa konfigürasyonu
st.set_page_config(page_title="Indices Map Tool", layout="wide")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- 1. SESSION STATE ---
for key, val in [('map_center', [38.9, 35.5]), ('map_zoom', 5), ('map_rendered', False), ('map_trigger', 0), 
                 ('applied_sel_one', []), ('applied_one_conf', {}), ('applied_multi_bundle', ([], {}))]:
    if key not in st.session_state: st.session_state[key] = val

from core.data_loader import load_turkiye_shp, list_available_indices, load_stats
from app.sidebar import render_sidebar, get_clean_name_logic
from viz.map_engine import create_interactive_map
import leafmap.foliumap as leafmap
from config.settings import FUTURE_SSP245_DIR, FUTURE_SSP245_STATS, INDICES_DIR

# --- CSS (Genel Görsel Ayarlar) ---
st.markdown("<style>.main .block-container { padding-top: 5rem !important; } footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# --- 2. VERİ ÖN YÜKLEME ---
shp = load_turkiye_shp()

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
def render_isolated_map_section(trigger):
    if st.session_state.map_rendered:
        sel = st.session_state.applied_sel_one
        conf = st.session_state.applied_one_conf
        multi = st.session_state.applied_multi_bundle

        # Birimleri total_stats üzerinden çekiyoruz
        units_data = {k: total_stats.get(k, {}).get('unit', '') for k in list(set(sel) | set(multi[0]))}

        # Haritayı oluştur (Yol haritasını engine_path_map ile gönderiyoruz)
        m = create_interactive_map(shp, (sel, conf), multi, units_data, engine_path_map)
        
        # Haritayı ekrana bas
        output = m.to_streamlit(height=1200, key="main_map_stable_key")
        
        # Zoom/Center güncellemeleri
        if isinstance(output, dict) and "center" in output and output["center"]:
            st.session_state.map_center = [output["center"]["lat"], output["center"]["lng"]]
            st.session_state.map_zoom = output["zoom"]
    else:
        # Boş başlangıç haritası
        m = leafmap.Map(center=[38.9, 35.5], zoom=5, tiles=None)
        if shp is not None:
            temp_shp = shp[['ADM1_TR', 'geometry']].copy(); temp_shp.columns = ['TR', 'geometry']
            m.add_gdf(temp_shp, layer_name="Türkiye Provinces", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.0})
        m.to_streamlit(height=1200, key="stable_map_render")

render_isolated_map_section(st.session_state.map_trigger)