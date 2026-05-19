"""
app/sidebar.py — v2.1

Reverts the v3 fragment split (which broke the immediate-config-on-tick
behavior). Keeps:
  - SSP scenario labels: Low-Emission, Intermediate, High-Emission
  - Updated About panel with dates and scenario explanations
"""

from __future__ import annotations
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from utils.naming import IndexFile, filter_files
from utils.indices_catalog import (
    INDICES_CATALOG,
    SUBCATEGORIES,
    CATEGORY_LABELS,
    SUBCATEGORY_LABELS,
)


# ===========================================================================
# Small helpers
# ===========================================================================

SCENARIO_LABELS = {
    "ssp126": "Low-Emission (SSP126)",
    "ssp245": "Intermediate (SSP245)",
    "ssp585": "High-Emission (SSP585)",
}


def _thin_divider() -> None:
    DIVIDER_COLOR = "#888a8d"
    st.markdown(
        f'<hr style="border: none; border-top: 1.5px solid {DIVIDER_COLOR}; '
        f'margin: 2px 0 12px 0;">',
        unsafe_allow_html=True,
    )


def _label_for(f: IndexFile) -> str:
    return f"{f.display_code} - {f.long_name}"


def _source_tag(f: IndexFile) -> str:
    if f.kind == "historical":
        return "Historical"
    return f"{(f.scenario or '').upper()} | {f.period}"


def _config_block_title(f: IndexFile) -> str:
    return f"{_label_for(f)} ({_source_tag(f)})"


def _stats_minmax(f: IndexFile) -> Tuple[float, float]:
    lo = f.stat_min if f.stat_min is not None else 0.0
    hi = f.stat_max if f.stat_max is not None else 100.0
    if lo == hi:
        hi = lo + 1.0
    return float(lo), float(hi)


def _files_index(files: List[IndexFile]) -> Dict[str, IndexFile]:
    return {f.filename: f for f in files}


def _period_display_label(period: str) -> str:
    mapping = {
        "2041-2060": "Middle of the Century (2041-2060)",
        "2081-2100": "End of the Century (2081-2100)",
    }
    return mapping.get(period, period)


def _legend_prefix_for(f: IndexFile) -> str:
    if f.kind == "historical":
        return "Hist: "
    scen = (f.scenario or "").upper()
    when = "Mid" if f.period == "2041-2060" else (
        "End" if f.period == "2081-2100" else f.period
    )
    return f"{scen} {when}: "


# ===========================================================================
# Per-indice configuration block (Interval/Threshold, palettes, etc.)
# ===========================================================================

def _render_config_block(f: IndexFile, prefix: str) -> dict:
    fn = f.filename
    conf: dict = {}
    d_min, d_max = _stats_minmax(f)

    conf["visible"] = st.toggle(
        "Visible on Map", value=True, key=f"vis_{prefix}_{fn}"
    )
    conf["unit"] = f.unit
    _thin_divider()

    mode = st.radio("Mode", ["Interval", "Threshold"], key=f"mod_{prefix}_{fn}")
    conf["mode"] = mode

    if mode == "Interval":
        use_slider = st.toggle(
            "Slider Control", value=True, key=f"use_sl_{prefix}_{fn}"
        )
        if not use_slider:
            col_min, col_max = st.columns(2)
            v_min = col_min.number_input(
                "Min", value=float(d_min), key=f"n_min_{prefix}_{fn}"
            )
            v_max = col_max.number_input(
                "Max", value=float(d_max), key=f"n_max_{prefix}_{fn}"
            )
            conf["vmin"], conf["vmax"] = v_min, v_max
        else:
            st.markdown(
                '<div style="display: flex; justify-content: space-between; '
                'font-size: 13px; font-weight: bold; margin-bottom: 10px; '
                'margin-top: 0px;"><span>Min</span><span>Max</span></div>',
                unsafe_allow_html=True,
            )
            r = st.slider(
                "Interval Slider",
                float(d_min),
                float(d_max),
                (float(d_min), float(d_max)),
                step=1.0,
                key=f"sl_{prefix}_{fn}",
                label_visibility="collapsed",
            )
            conf["vmin"], conf["vmax"] = r

        _thin_divider()
        conf["sub_mode"] = st.selectbox(
            "Figure Mode",
            ["Multi-Color", "One-Color"],
            key=f"sub_{prefix}_{fn}",
        )

        if conf["sub_mode"] == "Multi-Color":
            raw_palettes = sorted(
                [
                    "Blues", "BrBG", "BuGn", "BuPu", "GnBu", "Greens", "Greys",
                    "Oranges", "OrRd", "PiYG", "PRGn", "PuBu", "PuBuGn", "PuOr",
                    "PuRd", "Purples", "RdBu", "RdGy", "RdPu", "RdYlBu",
                    "RdYlGn", "Reds", "Spectral", "YlGn", "YlGnBu", "YlOrBr",
                    "YlOrRd", "viridis", "plasma", "inferno", "magma",
                    "cividis", "terrain", "gist_earth", "cubehelix", "coolwarm",
                ],
                key=str.lower,
            )
            col_pal, col_rev = st.columns([0.5, 0.5])
            with col_pal:
                default_idx = (
                    raw_palettes.index("RdYlBu") if "RdYlBu" in raw_palettes else 0
                )
                selected_base = st.selectbox(
                    "Color Palette",
                    raw_palettes,
                    index=default_idx,
                    key=f"cp_base_{prefix}_{fn}",
                )
            with col_rev:
                st.markdown(
                    '<div style="padding-top: 35px;"></div>',
                    unsafe_allow_html=True,
                )
                is_reversed = st.checkbox(
                    "Reverse", value=True, key=f"cp_rev_{prefix}_{fn}"
                )
            conf["cmap"] = (
                f"{selected_base}_r" if is_reversed else selected_base
            )

            gradient = np.linspace(0, 1, 256).reshape(1, -1)
            fig, ax = plt.subplots(figsize=(6, 0.18))
            ax.imshow(gradient, aspect="auto", cmap=plt.get_cmap(conf["cmap"]))
            ax.set_axis_off()
            st.pyplot(fig)
            plt.close(fig)

            col1, col2 = st.columns(2)
            conf["ext_min"] = col1.checkbox(
                "Extend Min", value=True, key=f"exmin_{prefix}_{fn}"
            )
            conf["ext_max"] = col2.checkbox(
                "Extend Max", value=True, key=f"exmax_{prefix}_{fn}"
            )
            conf["disc"] = st.toggle(
                "Discrete", value=True, key=f"ds_{prefix}_{fn}"
            )
            if conf["disc"]:
                conf["lv"] = st.number_input(
                    "Levels", 2, 20, 10, key=f"lv_{prefix}_{fn}"
                )
        else:
            conf["one_c"] = st.color_picker(
                "Color", "#DC7933", key=f"c_{prefix}_{fn}"
            )

    else:  # Threshold mode
        use_slider_th = st.toggle(
            "Slider Control", value=True, key=f"use_sl_th_{prefix}_{fn}"
        )
        init_val = float((d_min + d_max) / 2)
        if use_slider_th:
            st.markdown(
                '<div style="display: flex; justify-content: space-between; '
                'font-size: 13px; font-weight: bold; margin-bottom: 10px; '
                'margin-top: 0px;"><span>Min</span><span>Max</span></div>',
                unsafe_allow_html=True,
            )
            th_val = st.slider(
                "Threshold Slider",
                min_value=float(d_min),
                max_value=float(d_max),
                value=init_val,
                step=1.0,
                key=f"sl_th_{prefix}_{fn}",
                label_visibility="collapsed",
            )
        else:
            th_val = st.number_input(
                "Threshold Value",
                value=init_val,
                key=f"num_th_{prefix}_{fn}",
                label_visibility="collapsed",
            )
        conf["thresh"] = th_val
        _thin_divider()

        col_b, col_a = st.columns(2)
        conf["b_c"] = col_b.color_picker(
            "Lower", "#4747B5", key=f"bc_{prefix}_{fn}"
        )
        conf["b_m"] = (
            "Color"
            if not col_b.toggle("No Color", key=f"nb_{prefix}_{fn}")
            else "No Color"
        )
        conf["a_c"] = col_a.color_picker(
            "Higher", "#C93131", key=f"ac_{prefix}_{fn}"
        )
        conf["a_m"] = (
            "Color"
            if not col_a.toggle("No Color ", key=f"na_{prefix}_{fn}")
            else "No Color"
        )

    conf["alpha"] = st.slider(
        "Opacity", 0.0, 1.0, 0.7, step=0.05, key=f"al_{prefix}_{fn}"
    )
    return conf


# ===========================================================================
# Index list rendering (the hierarchy)
# ===========================================================================

def _render_indice_list(
    files_subset: List[IndexFile], prefix: str
) -> List[str]:
    selected: List[str] = []
    for f in sorted(files_subset, key=lambda x: x.display_code):
        if st.checkbox(_label_for(f), key=f"chk_{prefix}_{f.filename}"):
            selected.append(f.filename)
    return selected


def _render_two_level_picker(
    files_subset: List[IndexFile], prefix: str
) -> List[str]:
    selected: List[str] = []
    for category in ["CLIMATE", "BIO_CLIMATE"]:
        cat_files = [f for f in files_subset if f.category == category]
        if not cat_files:
            continue
        cat_label = CATEGORY_LABELS[category]
        with st.expander(cat_label, expanded=False):
            for sub in SUBCATEGORIES[category]:
                sub_files = [f for f in cat_files if f.subcategory == sub]
                if not sub_files:
                    continue
                sub_label = SUBCATEGORY_LABELS[sub]
                with st.expander(f"{sub_label} ({len(sub_files)})",
                                 expanded=False):
                    sel = _render_indice_list(sub_files, f"{prefix}_{sub}")
                    selected.extend(sel)
    return selected


# ===========================================================================
# Tab 1: Single-Indice — wrapped in @st.fragment (deferred update for map)
# ===========================================================================

@st.fragment
def _single_indice_tab_fragment(files: List[IndexFile]) -> None:
    all_selected: List[str] = []

    with st.expander("Historical", expanded=False):
        hist_files = filter_files(files, kind="historical")
        sel = _render_two_level_picker(hist_files, prefix="one_h")
        all_selected.extend(sel)

    with st.expander("Future", expanded=False):
        future_files = filter_files(files, kind="future")
        for scenario in ["ssp126", "ssp245", "ssp585"]:
            scen_files = [f for f in future_files if f.scenario == scenario]
            if not scen_files:
                continue
            scen_label = SCENARIO_LABELS[scenario]
            with st.expander(scen_label, expanded=False):
                periods = sorted({f.period for f in scen_files})
                for period in periods:
                    period_files = [f for f in scen_files if f.period == period]
                    period_label = _period_display_label(period)
                    with st.expander(period_label, expanded=False):
                        sel = _render_two_level_picker(
                            period_files,
                            prefix=f"one_f_{scenario}_{period}",
                        )
                        all_selected.extend(sel)

    # Config blocks per ticked indice (rendered immediately, same fragment)
    conf_by_filename: dict = {}
    if all_selected:
        st.markdown(
            '<div style="margin-top: 20px;"></div>', unsafe_allow_html=True
        )
        _thin_divider()

        idx = _files_index(files)
        for fn in all_selected:
            f = idx[fn]
            with st.expander(_config_block_title(f), expanded=True):
                conf = _render_config_block(f, prefix="one")
                conf["legend_prefix"] = _legend_prefix_for(f)
                conf_by_filename[fn] = conf

    st.session_state.draft_one = (all_selected, conf_by_filename)


# ===========================================================================
# Tab 2: Multi-Indices — wrapped in @st.fragment too
# ===========================================================================

@st.fragment
def _multi_indice_tab_fragment(files: List[IndexFile]) -> None:
    selected_filenames: List[str] = []
    idx = _files_index(files)

    with st.expander("Historical", expanded=False):
        hist_files = filter_files(files, kind="historical")
        sel = _render_two_level_picker(hist_files, prefix="m_h")
        selected_filenames.extend(sel)

    with st.expander("Future", expanded=False):
        future_files = filter_files(files, kind="future")
        for scenario in ["ssp126", "ssp245", "ssp585"]:
            scen_files = [f for f in future_files if f.scenario == scenario]
            if not scen_files:
                continue
            scen_label = SCENARIO_LABELS[scenario]
            with st.expander(scen_label, expanded=False):
                periods = sorted({f.period for f in scen_files})
                for period in periods:
                    period_files = [f for f in scen_files if f.period == period]
                    period_label = _period_display_label(period)
                    with st.expander(period_label, expanded=False):
                        sel = _render_two_level_picker(
                            period_files,
                            prefix=f"m_f_{scenario}_{period}",
                        )
                        selected_filenames.extend(sel)

    all_ind_conf: dict = {}
    m_color = "#2FA42F"
    m_alpha = 0.8

    if selected_filenames:
        st.markdown(
            '<div style="margin-top: 25px;"></div>', unsafe_allow_html=True
        )
        _thin_divider()

        for fn in selected_filenames:
            f = idx[fn]
            legend_name = f"{_legend_prefix_for(f)}{_label_for(f)}"

            with st.expander(_config_block_title(f), expanded=True):
                m_min, m_max = _stats_minmax(f)
                use_slider_m = st.toggle(
                    "Slider Control", value=True, key=f"use_sl_m_{fn}"
                )
                if use_slider_m:
                    st.markdown(
                        '<div style="display: flex; justify-content: space-between; '
                        'font-size: 13px; font-weight: bold; margin-bottom: 10px; '
                        'margin-top: 0px;"><span>Min</span><span>Max</span></div>',
                        unsafe_allow_html=True,
                    )
                    r = st.slider(
                        "Multi Range Slider",
                        float(m_min),
                        float(m_max),
                        (float(m_min), float(m_max)),
                        step=1.0,
                        key=f"rs_m_{fn}",
                        label_visibility="collapsed",
                    )
                    v_min_final, v_max_final = r[0], r[1]
                else:
                    col1, col2 = st.columns(2)
                    v_min_final = col1.number_input(
                        "Min", value=float(m_min), key=f"n_min_m_{fn}"
                    )
                    v_max_final = col2.number_input(
                        "Max", value=float(m_max), key=f"n_max_m_{fn}"
                    )

                all_ind_conf[fn] = {
                    "vmin": v_min_final,
                    "vmax": v_max_final,
                    "legend_name": legend_name,
                }

        m_color = st.color_picker(
            "Synthesis Color", "#2FA42F", key="m_g_cp"
        )
        m_alpha = st.slider(
            "Synthesis Opacity", 0.0, 1.0, 0.8, step=0.05, key="m_g_al"
        )

    st.session_state.draft_multi = (
        selected_filenames,
        {"indices": all_ind_conf, "color": m_color, "alpha": m_alpha},
    )


# ===========================================================================
# About panel (pinned at the bottom)
# ===========================================================================

def _render_about_panel() -> None:
    with st.expander("About", expanded=False):
        st.markdown(
            "**Climate Indices Map Tool**\n\n"
            "Visualizes 64 climate and bio-climate indices for Türkiye, "
            "computed from 1 km daily CHELSA observed climatology (1995-2014) "
            "and from a 10-member ensemble of 0.5° daily GCMs projected to "
            "mid-century (2041-2060) and end-century (2081-2100) under three "
            "SSP scenarios:\n"
            "- **SSP126** — Low-Emission (sustainable, optimistic)\n"
            "- **SSP245** — Intermediate (middle-of-the-road)\n"
            "- **SSP585** — High-Emission (fossil-fueled, pessimistic)\n\n"
            "Indices are organized into:\n"
            "- **Climate Indices** — Temperature, Precipitation, Drought, "
            "Energy, Agriculture\n"
            "- **Bio-Climate Indices** — Human Comfort, "
            "Agriculture & Livestock, Atmospheric Comfort"
        )

        with st.expander("Indices Reference", expanded=False):
            st.caption(
                "Code, full name, formula and unit for all 64 indices. "
                "Bio-climate indices are summarized via their input variables."
            )
            for cat in ["CLIMATE", "BIO_CLIMATE"]:
                st.markdown(f"**{CATEGORY_LABELS[cat]}**")
                for sub in SUBCATEGORIES[cat]:
                    items = [
                        (k, v) for k, v in INDICES_CATALOG.items()
                        if v["category"] == cat and v["subcategory"] == sub
                    ]
                    if not items:
                        continue
                    st.markdown(f"*{SUBCATEGORY_LABELS[sub]}*")
                    for code, entry in sorted(items, key=lambda x: x[0]):
                        st.markdown(
                            f"- **{entry['display_code']}** — "
                            f"{entry['long_name']}  \n"
                            f"  `{entry['formula']}`  ·  "
                            f"*unit:* `{entry['unit']}`"
                        )
                st.markdown("---")


# ===========================================================================
# Public entry points
# ===========================================================================

def render_sidebar(
    files: List[IndexFile],
) -> Tuple[Tuple[List[str], dict], Tuple[List[str], dict]]:
    if "draft_one" not in st.session_state:
        st.session_state.draft_one = ([], {})
    if "draft_multi" not in st.session_state:
        st.session_state.draft_multi = ([], {})

    st.sidebar.title("Indices Map Tool")
    with st.sidebar:
        tab1, tab2 = st.tabs(["Single-Indice", "Multi-Indices"])
        with tab1:
            _single_indice_tab_fragment(files)
        with tab2:
            _multi_indice_tab_fragment(files)

    return st.session_state.draft_one, st.session_state.draft_multi


def render_about_at_bottom() -> None:
    with st.sidebar:
        st.markdown(
            '<div style="margin-top: 30px;"></div>', unsafe_allow_html=True
        )
        _thin_divider()
        _render_about_panel()