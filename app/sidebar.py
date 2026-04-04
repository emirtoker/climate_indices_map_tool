import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
import matplotlib
import os

matplotlib.use('Agg')

def thin_divider():
    DIVIDER_COLOR = "#888a8d"
    st.markdown(f'<hr style="border: none; border-top: 1.5px solid {DIVIDER_COLOR}; margin: 2px 0 12px 0;">', unsafe_allow_html=True)

def get_clean_name(file_name):
    """Kısaltmayı (PCD, DI vb.) her zaman BÜYÜK HARF yapar, açıklamayı Title Case yapar."""
    codes = ["PCD", "PRCPTOT", "SU", "TR", "DI", "HI", "PET", "SPI", "SPEI"]
    clean = file_name.replace(".tif", "").replace("_cog", "")
    parts = clean.split('_')
    
    found_code = None
    found_idx = -1
    
    # İsmi sondan başa tarayarak indisi bul (TR ülke koduyla karışmaması için)
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].upper() in codes:
            found_code = parts[i].upper() # Zorunlu Büyük Harf
            found_idx = i
            break
            
    if found_code:
        # Koddan sonraki kısmı Title Case yap (PCD - Passive Comfort Days)
        description = " ".join(parts[found_idx + 1:]).replace("_", " ").title()
        return f"{found_code} - {description}"
    
    return clean.replace("_", " ").title()

# --- SINGLE INDICE UI ---
@st.fragment
def render_single_indices_ui(available_dict, units_dict, stats, prefix="one"):
    LABEL_STYLE = '<p style="font-size: 14px; color: #eeeeee; margin-bottom: 2px; font-weight: 400;">'
    one_conf = {}
    selected_keys = []
    
    sorted_keys = sorted(available_dict.keys())
    for file_key in sorted_keys:
        display_name = get_clean_name(file_key)
        if st.checkbox(display_name, key=f"{prefix}_check_{file_key}"):
            selected_keys.append(file_key)
    
    if selected_keys:
        st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)
        thin_divider()
        for file_key in selected_keys:
            display_name = get_clean_name(file_key)
            with st.expander(display_name, expanded=True):
                conf = {'visible': st.toggle("Visible on Map", value=True, key=f"vis_{prefix}_{file_key}")}
                thin_divider()
                
                d_min, d_max = (float(np.floor(stats[file_key]["min"])), float(np.ceil(stats[file_key]["max"]))) if stats and file_key in stats else (0.0, 100.0)
                conf['unit'] = stats.get(file_key, {}).get('unit', '')
                
                mode = st.radio("Mode", ["Interval", "Threshold"], key=f"mod_{prefix}_{file_key}")
                conf['mode'] = mode
                thin_divider()
                
                if mode == "Interval":
                    use_slider = st.toggle("Slider Control", value=False, key=f"use_sl_{prefix}_{file_key}")
                    if not use_slider:
                        col_min, col_max = st.columns(2)
                        with col_min: v_min = st.number_input("Min", value=d_min, key=f"num_min_{prefix}_{file_key}")
                        with col_max: v_max = st.number_input("Max", value=d_max, key=f"num_max_{prefix}_{file_key}")
                        conf['vmin'], conf['vmax'] = v_min, v_max
                    else:
                        range_values = st.slider("Range Selector", d_min, d_max, (d_min, d_max), step=1.0, key=f"sl_bar_{prefix}_{file_key}", label_visibility="collapsed")
                        conf['vmin'], conf['vmax'] = range_values

                    thin_divider()
                    conf['sub_mode'] = st.selectbox("Figure Mode", ["Multi-Color", "One-Color"], key=f"sub_{prefix}_{file_key}")
                    if conf['sub_mode'] == "Multi-Color":
                        conf['cmap'] = st.selectbox("Color Palette", [
        "RdYlBu_r", "Spectral_r", "coolwarm", "RdBu_r", "BrBG",
        "viridis", "magma", "inferno", "plasma",
        "Blues", "Reds", "Greens", "Oranges", "Purples", "YlOrRd", "YlGnBu",
        "terrain", "gist_earth", "cubehelix"
    ], key=f"cp_{prefix}_{file_key}")
                        
                        gradient = np.linspace(0, 1, 256).reshape(1, -1); fig, ax = plt.subplots(figsize=(6, 0.18)) 
                        ax.imshow(gradient, aspect='auto', cmap=plt.get_cmap(conf['cmap']))
                        for spine in ax.spines.values(): spine.set_linewidth(0.3); spine.set_color('lightgrey')
                        ax.set_xticks([]); ax.set_yticks([]); st.pyplot(fig); plt.close(fig)
                        
                        col_ext1, col_ext2 = st.columns(2)
                        with col_ext1: conf['ext_min'] = st.checkbox("Extend Min", value=True, key=f"exmin_{prefix}_{file_key}")
                        with col_ext2: conf['ext_max'] = st.checkbox("Extend Max", value=True, key=f"exmax_{prefix}_{file_key}")
                        thin_divider()
                        conf['disc'] = st.toggle("Discrete Values", value=True, key=f"ds_{prefix}_{file_key}")
                        if conf['disc']: conf['lv'] = st.number_input("Levels", 2, 20, 10, key=f"lv_{prefix}_{file_key}")
                    else:
                        conf['one_c'] = st.color_picker("Color", "#DC7933", key=f"c_{prefix}_{file_key}")
                else:
                    conf['thresh'] = st.number_input("Threshold Value", value=float((d_min+d_max)/2), key=f"th_val_{prefix}_{file_key}")
                    col_b, col_a = st.columns(2)
                    with col_b: conf['b_c'] = st.color_picker("Below", "#4747B5", key=f"bc_{prefix}_{file_key}"); conf['b_m'] = "Color"
                    with col_a: conf['a_c'] = st.color_picker("Above", "#C93131", key=f"ac_{prefix}_{file_key}"); conf['a_m'] = "Color"

                conf['alpha'] = st.slider("Opacity", 0.0, 1.0, 0.7, key=f"al_{prefix}_{file_key}")
                one_conf[file_key] = conf
                
    return [k for k in sorted(available_dict.keys()) if st.session_state.get(f"{prefix}_check_{k}")], one_conf

# --- MULTI INDICES UI (Fragment) ---
@st.fragment
def render_multi_indices_ui_fragment(av_dict_hist, av_dict_future, stats_hist, stats_future):
    selected_meta = [] # (file_key, legend_display_name, stats)
    
    def ssp_filter(d, period):
        return {k: v for k, v in d.items() if period in k}

    # 1. Aşama: Hiyerarşik Seçim
    with st.expander("CHELSA Historical (1995-2014)", expanded=False):
        for k in sorted(av_dict_hist.keys()):
            # Legend İsmi: Hist: PCD - Passive Comfort Days
            legend_label = f"Hist: {get_clean_name(k)}"
            if st.checkbox(get_clean_name(k), key=f"m_check_h_{k}"):
                selected_meta.append((k, legend_label, stats_hist))
    
    with st.expander("CHELSA+GCMs Future", expanded=False):
        st.info("SSP126 (Empty)")
        with st.expander("SSP245", expanded=True):
            with st.expander("Middle of the Century (2041-2060)", expanded=False):
                f_mid = ssp_filter(av_dict_future, "2041-2060")
                for k in sorted(f_mid.keys()):
                    legend_label = f"SSP245 Mid: {get_clean_name(k)}"
                    if st.checkbox(get_clean_name(k), key=f"m_check_fm_{k}"):
                        selected_meta.append((k, legend_label, stats_future))
            with st.expander("End of the Century (2081-2100)", expanded=False):
                f_end = ssp_filter(av_dict_future, "2081-2100")
                for k in sorted(f_end.keys()):
                    legend_label = f"SSP245 End: {get_clean_name(k)}"
                    if st.checkbox(get_clean_name(k), key=f"m_check_fe_{k}"):
                        selected_meta.append((k, legend_label, stats_future))
        st.info("SSP585 (Empty)")

    # 2. Aşama: Toplu Ayarlar
    all_sel_m, all_ind_conf = [], {}
    m_color, m_alpha = "#2FA42F", 0.8
    
    if selected_meta:
        st.markdown('<div style="margin-top: 25px;"></div>', unsafe_allow_html=True)
        st.subheader("Synthesis Intersection Settings")
        thin_divider()
        
        for file_key, legend_name, stats_src in selected_meta:
            with st.expander(legend_name, expanded=True):
                d_min_m, d_max_m = (float(stats_src[file_key]["min"]), float(stats_src[file_key]["max"])) if stats_src and file_key in stats_src else (0.0, 100.0)
                m_range = st.slider("Target Range", d_min_m, d_max_m, (d_min_m, d_max_m), step=1.0, key=f"rs_m_{file_key}")
                all_sel_m.append(file_key)
                # Map Engine lejantı için temiz ismi saklıyoruz
                all_ind_conf[file_key] = {'vmin': m_range[0], 'vmax': m_range[1], 'legend_name': legend_name}
        
        m_color = st.color_picker("Synthesis Color", "#2FA42F", key="m_global_cp")
        m_alpha = st.slider("Synthesis Opacity", 0.0, 1.0, 0.8, key="m_global_al")

    return all_sel_m, {'indices': all_ind_conf, 'color': m_color, 'alpha': m_alpha}

# --- ANA RENDER ---
def render_sidebar(av_dict_hist, av_dict_future, units_dict_hist, units_dict_future, stats_hist, stats_future):
    st.sidebar.title("Indices Map Tool")
    tab_single, tab_multi = st.sidebar.tabs(["Single-Indice", "Multi-Indices"])

    def ssp_filter(d, period):
        return {k: v for k, v in d.items() if period in k}

    with tab_single:
        all_sel_one, all_conf_one = [], {}
        with st.expander("CHELSA Historical (1995-2014)", expanded=False):
            sel, conf = render_single_indices_ui(av_dict_hist, units_dict_hist, stats_hist, prefix="one_h")
            all_sel_one.extend(sel); all_conf_one.update(conf)
            
        with st.expander("CHELSA+GCMs Future", expanded=False):
            st.info("SSP126 (Empty)")
            with st.expander("SSP245", expanded=True):
                with st.expander("Middle of the Century (2041-2060)", expanded=False):
                    sel, conf = render_single_indices_ui(ssp_filter(av_dict_future, "2041-2060"), units_dict_future, stats_future, prefix="one_fm")
                    all_sel_one.extend(sel); all_conf_one.update(conf)
                with st.expander("End of the Century (2081-2100)", expanded=False):
                    sel, conf = render_single_indices_ui(ssp_filter(av_dict_future, "2081-2100"), units_dict_future, stats_future, prefix="one_fe")
                    all_sel_one.extend(sel); all_conf_one.update(conf)
            st.info("SSP585 (Empty)")
        one_bundle = (all_sel_one, all_conf_one)

    with tab_multi:
        multi_bundle = render_multi_indices_ui_fragment(av_dict_hist, av_dict_future, stats_hist, stats_future)

    return one_bundle, multi_bundle