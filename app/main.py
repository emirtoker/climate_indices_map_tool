import sys, os
import time 
import matplotlib
matplotlib.use('Agg') 
import concurrent.futures
import streamlit as st

# Gereksiz karmaşayı ve hata riskini sıfırlamak için 
# o brittle (kırılgan) context importlarını tamamen sildik.

st.set_page_config(page_title="Indices Map Tool", layout="wide")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- 1. SESSION STATE (Mühürlü Kasa) ---
if 'map_center' not in st.session_state: st.session_state.map_center = [38.9, 35.5]
if 'map_zoom' not in st.session_state: st.session_state.map_zoom = 5
if 'map_rendered' not in st.session_state: st.session_state.map_rendered = False
if 'map_trigger' not in st.session_state: st.session_state.map_trigger = 0

if 'applied_sel_one' not in st.session_state: st.session_state.applied_sel_one = []
if 'applied_one_conf' not in st.session_state: st.session_state.applied_one_conf = {}
if 'applied_multi_bundle' not in st.session_state: st.session_state.applied_multi_bundle = ([], {})

from core.data_loader import load_index_data, load_turkiye_shp, list_available_indices, load_stats
from app.sidebar import render_sidebar
from viz.map_engine import create_interactive_map
import leafmap.foliumap as leafmap

# --- CSS (Senin Orijinal CSS Ayarların) ---
st.markdown("""
    <style>
    .leaflet-control-container .leaflet-top.leaflet-right {
        display: flex !important;
        flex-wrap: wrap-reverse !important;
        flex-direction: row-reverse !important;
        justify-content: flex-start !important;
        align-content: flex-start !important;
        top: 100px !important;
        right: 10px !important;
    }
    .main .block-container { padding-top: 5rem !important; }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# VERİ ÖN YÜKLEME
shp = load_turkiye_shp()
av_dict = list_available_indices()
stats = load_stats()

# 2. SIDEBAR RENDER
one_bundle, multi_bundle = render_sidebar(av_dict, {}, {}, stats)
current_sel_one, current_one_conf = one_bundle
current_sel_multi, current_multi_conf = multi_bundle

# --- UPDATE MAP BUTONU ---
with st.sidebar:
    st.markdown("---")
    if st.button("Update Map", use_container_width=True, type="primary", key="main_update_btn"):
        st.session_state.applied_one_conf = current_one_conf.copy()
        st.session_state.applied_sel_one = current_sel_one.copy()
        if current_sel_multi:
            st.session_state.applied_multi_bundle = (current_sel_multi, current_multi_conf)
            st.session_state.synthesis_active = True
        else:
            st.session_state.applied_multi_bundle = ([], {})
            st.session_state.synthesis_active = False
        st.session_state.map_trigger += 1 
        st.session_state.map_rendered = True
        st.rerun()

# --- 3. HARİTA BÖLÜMÜ (FRAGMENT - PARALEL MOTOR) ---
@st.cache_resource(show_spinner="Harita katmanları hazırlanıyor...")
def get_cached_map(applied_sel, applied_conf, applied_multi, _shp, _av_dict, _units_data):
    """
    Parametrelerin önüne '_' koyarak Streamlit'e 'bunları hash'leme (izleme), 
    sadece referans al' diyoruz. Bu hem hatayı önler hem de hızı artırır.
    """
    return create_interactive_map(
        _shp, 
        (applied_sel, applied_conf), 
        applied_multi, 
        _units_data, 
        _av_dict
    )

@st.fragment
def render_isolated_map_section(trigger):
    is_renderable = (len(st.session_state.applied_sel_one) > 0 or st.session_state.get('synthesis_active'))
    
    if is_renderable and st.session_state.map_rendered:
        applied_sel = st.session_state.applied_sel_one
        applied_conf = st.session_state.applied_one_conf
        applied_multi = st.session_state.applied_multi_bundle

        load_list = list(set(applied_sel) | set(applied_multi[0]))
        units_data = {} 
        load_errors = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_index = {executor.submit(load_index_data, av_dict[k]): k for k in load_list}
            for future in concurrent.futures.as_completed(future_to_index):
                k = future_to_index[future]
                try:
                    # Sadece metadata (birim) alıyoruz, devasa matris RAM'i şişirmiyor
                    _, _, u = future.result() 
                    units_data[k] = u
                except Exception as e:
                    load_errors.append(f"{k}: {e}")
        
        for err in load_errors: st.error(err)

        # --- KRİTİK DÜZELTME: Parametre sayıları eşitlendi (6 argüman) ---
        m = get_cached_map(
            tuple(applied_sel), 
            applied_conf,       
            applied_multi,      
            shp, 
            av_dict, 
            units_data
        )
        
        output = m.to_streamlit(height=1200, key="main_map_stable_key")
        
        if isinstance(output, dict) and "center" in output and output["center"]:
            st.session_state.map_center = [output["center"]["lat"], output["center"]["lng"]]
            st.session_state.map_zoom = output["zoom"]
    else:
        m = leafmap.Map(center=[38.9, 35.5], zoom=5, tiles=None)
        if shp is not None:
            temp_shp = shp[['ADM1_TR', 'geometry']].copy(); temp_shp.columns = ['TR', 'geometry']
            m.add_gdf(temp_shp, layer_name="Türkiye Provinces", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.0})
        m.to_streamlit(height=1200, key="initial_empty_map")

render_isolated_map_section(st.session_state.map_trigger)