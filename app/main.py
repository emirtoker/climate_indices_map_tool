"""
app/main.py

Top-level Streamlit orchestrator.

Pipeline
--------
1. Load all index files (utils.naming.load_all_index_files) -> List[IndexFile]
2. Load static layers (shapefiles, LCZ)
3. Render sidebar -> returns (one_bundle, multi_bundle)
4. Render reference-layer UI (provinces, districts, OSM, LCZ toggles)
5. On "Update Map": freeze selections into session state, bump trigger
6. Fragment-isolated map render reads session state and draws

Why fragments?
--------------
Reference-layer checkboxes (provinces/districts/etc.) and the heavy map
render are decoupled into their own `@st.fragment`s so flipping a checkbox
does NOT force a full re-render of the sidebar or the map. The map only
re-renders when the trigger int changes (after "Update Map" is clicked).
"""

import os
import sys

import folium
import leafmap.foliumap as leafmap
import streamlit as st

# --- PATH BOOTSTRAP ---------------------------------------------------------
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CURRENT_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.sidebar import render_sidebar, render_about_at_bottom
from core.data_loader import (
    load_turkiye_shp,
    load_districts_shp,
    load_lcz_static,
)
from utils.naming import load_all_index_files
from viz.map_engine import create_interactive_map


# ---------------------------------------------------------------------------
# LCZ fallback legend (used by the placeholder map before "Update Map")
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Page config + global CSS
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Indices Map Tool", layout="wide")

st.markdown(
    "<style>"
    ".main .block-container { padding-top: 5rem !important; } "
    "footer {visibility: hidden;}"
    "/* caption (small grey heading) alt bosluk sifir */ "
    "section[data-testid='stSidebar'] p { margin-bottom: 0 !important; } "
    "section[data-testid='stSidebar'] [data-testid='stCaptionContainer'] "
    "{ margin: 0 0 -0.6rem 0 !important; padding: 0 !important; } "
    "/* tab bar ust bosluk sifir */ "
    "section[data-testid='stSidebar'] [data-testid='stTabs'] "
    "{ margin-top: -0.6rem !important; } "
    "section[data-testid='stSidebar'] [data-baseweb='tab-list'] "
    "{ margin-top: 0 !important; padding-top: 0 !important; } "
    "/* genel dikey element araligini kis */ "
    "section[data-testid='stSidebar'] [data-testid='stVerticalBlock'] "
    "{ gap: 0.3rem !important; } "
    "</style>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

_INIT_VALS = [
    ("map_center",            [38.9, 35.5]),
    ("map_zoom",              5),
    ("map_rendered",          False),
    ("map_trigger",           0),
    ("applied_sel_one",       []),
    ("applied_one_conf",      {}),
    ("applied_multi_bundle",  ([], {})),
    ("app_show_provinces",    True),
    ("app_show_districts",    True),
    ("app_show_osm",          True),
    ("app_show_lcz",          True),
    ("app_lcz_alpha",         0.4),
    ("ui_provinces",          True),
    ("ui_districts",          True),
    ("ui_osm",                True),
    ("ui_lcz",                True),
    ("ui_alpha",              0.4),
    ("synthesis_active",      False),
]
for _k, _v in _INIT_VALS:
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ---------------------------------------------------------------------------
# Data preload
# ---------------------------------------------------------------------------

shp = load_turkiye_shp()
districts_shp = load_districts_shp()

# All 448 index TIFs, discovered + parsed + merged with catalog + stats.
# Cached implicitly through naming module (no Streamlit cache here, but cheap).
files = load_all_index_files()

# Fast lookup by filename — used by map_engine to resolve path & metadata.
index_by_filename = {f.filename: f for f in files}


# ---------------------------------------------------------------------------
# Sidebar render
# ---------------------------------------------------------------------------

one_bundle, multi_bundle = render_sidebar(files)


# ---------------------------------------------------------------------------
# Reference-layers fragment (isolated, so toggles don't rerun the map)
# ---------------------------------------------------------------------------

@st.fragment
def render_reference_layers_ui():
    with st.container(border=True):
        st.subheader("Reference Layers")
        st.checkbox("Open Street Map", key="ui_osm")
        show_lcz = st.checkbox("Local Climate Zones", key="ui_lcz")
        if show_lcz:
            st.slider("LCZ Opacity", 0.0, 1.0, step=0.05, key="ui_alpha")
        st.checkbox("Türkiye Provinces", key="ui_provinces")
        st.checkbox("Türkiye Districts", key="ui_districts")


with st.sidebar:
    render_reference_layers_ui()
    st.markdown("---")

    # ---------- Update Map ----------
    if st.button("Update Map", use_container_width=True, type="primary"):
        st.session_state.applied_one_conf = one_bundle[1].copy()
        st.session_state.applied_sel_one = one_bundle[0].copy()
        st.session_state.applied_multi_bundle = (
            multi_bundle if multi_bundle[0] else ([], {})
        )
        st.session_state.synthesis_active = bool(multi_bundle[0])

        st.session_state.app_show_provinces = st.session_state.ui_provinces
        st.session_state.app_show_districts = st.session_state.ui_districts
        st.session_state.app_show_osm = st.session_state.ui_osm
        st.session_state.app_show_lcz = st.session_state.ui_lcz
        st.session_state.app_lcz_alpha = st.session_state.ui_alpha

        st.session_state.map_trigger += 1
        st.session_state.map_rendered = True
        st.rerun()

    # ---------- Reset Map ----------
    if st.button("Reset Map", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            if key not in ("map_center", "map_zoom"):
                del st.session_state[key]
        st.session_state.map_rendered = False
        st.rerun()

# Render About panel at the very bottom of the sidebar
render_about_at_bottom()


# ---------------------------------------------------------------------------
# Map render fragment (isolated, only re-runs when map_trigger changes)
# ---------------------------------------------------------------------------

@st.fragment
def render_isolated_map_section(trigger):
    """Render the main map, isolated from sidebar reruns.

    `trigger` is passed in so that incrementing st.session_state.map_trigger
    forces a fragment re-run (Streamlit re-runs a fragment when its inputs
    change).
    """
    show_p = st.session_state.app_show_provinces
    show_d = st.session_state.app_show_districts
    show_o = st.session_state.app_show_osm
    show_l = st.session_state.app_show_lcz
    alpha_l = st.session_state.app_lcz_alpha

    lcz_bundle = load_lcz_static() if show_l else (None, None)

    if st.session_state.map_rendered:
        sel = st.session_state.applied_sel_one
        conf = st.session_state.applied_one_conf
        multi = st.session_state.applied_multi_bundle

        m = create_interactive_map(
            shp=shp,
            districts_shp=districts_shp,
            one_bundle=(sel, conf),
            multi_bundle=multi,
            index_by_filename=index_by_filename,
            show_provinces=show_p,
            show_districts=show_d,
            show_osm=show_o,
            lcz_bundle=lcz_bundle,
            lcz_alpha=alpha_l,
        )
        m.to_streamlit(height=1200, key="main_map_stable_key")
    else:
        # Placeholder map: shown before the first "Update Map" click
        m = leafmap.Map(center=[38.9, 35.5], zoom=5, tiles=None)

        if show_o:
            folium.TileLayer(
                tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                attr="&copy; OSM", name="Open Street Map", overlay=True,
            ).add_to(m)

        if show_l and lcz_bundle[0]:
            folium.raster_layers.ImageOverlay(
                image=lcz_bundle[0], bounds=lcz_bundle[1],
                opacity=alpha_l, name="Local Climate Zones", zindex=4,
            ).add_to(m)
            m.get_root().html.add_child(folium.Element(LCZ_LEGEND_HTML))

        if show_p and shp is not None:
            temp_shp = shp[["ADM1_TR", "geometry"]].copy()
            temp_shp.columns = ["Şehir", "geometry"]
            m.add_gdf(
                temp_shp, layer_name="Türkiye Provinces",
                style={"color": "black", "fillOpacity": 0, "weight": 1.2},
            )

        if show_d and districts_shp is not None:
            temp_dist = districts_shp[["ADM1_TR", "ADM2_TR", "geometry"]].copy()
            temp_dist.columns = ["Şehir", "İlçe", "geometry"]
            temp_dist.loc[temp_dist["Şehir"] == temp_dist["İlçe"], "İlçe"] = (
                temp_dist["İlçe"] + " (Merkez)"
            )
            m.add_gdf(
                temp_dist, layer_name="Türkiye Districts",
                style={"color": "#444444", "fillOpacity": 0, "weight": 0.2},
            )

        m.to_streamlit(height=1200, key="stable_map_render")


render_isolated_map_section(st.session_state.map_trigger)