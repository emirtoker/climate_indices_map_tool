import sys, os
import streamlit as st

st.set_page_config(page_title="Indices Map Tool", layout="wide")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_loader import load_index_data, load_turkiye_shp, list_available_indices
from app.sidebar import render_sidebar
from viz.map_engine import create_interactive_map
import leafmap.foliumap as leafmap

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
        max-width: 650px !important; 
        background: transparent !important;
    }
    .leaflet-control-layers { font-size: 14px !important; border: none !important; }
    .main .block-container { padding-top: 5rem !important; }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

shp = load_turkiye_shp()
av_dict = list_available_indices()

all_requested = set()
for k in av_dict.keys():
    if st.session_state.get(f"one_check_{k}") or st.session_state.get(f"multi_check_{k}"):
        all_requested.add(k)

layers_data, units_data = {}, {}
for k in all_requested:
    d, _, u = load_index_data(av_dict[k])
    layers_data[k], units_data[k] = d, u

one_bundle, multi_bundle = render_sidebar(av_dict, layers_data, units_data)

show_map = False
if one_bundle and one_bundle[0]: show_map = True
if st.session_state.get('synthesis_active') and multi_bundle[0]: show_map = True

if show_map:
    m = create_interactive_map(layers_data, shp, one_bundle, multi_bundle, units_data)
    m.to_streamlit(height=850)
else:
    m = leafmap.Map(center=[39, 35], zoom=6, tiles=None, control_scale=True, zoom_snap=0.1, zoom_delta=0.1)
    if shp is not None:
        m.add_gdf(shp, layer_name="Türkiye Provinces", style={'color': 'black', 'fillOpacity': 0, 'weight': 1.0})
    m.to_streamlit(height=850)