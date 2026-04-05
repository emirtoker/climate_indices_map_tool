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

def get_clean_name_logic(file_name, is_historical=False):
    """
    Ham dosya isminden (filename) temiz isim üretir.
    Historical için 6. eleman taktiği, Future için sondan başa tarama.
    """
    codes = ["PCD", "PRCPTOT", "SU", "TR", "DI", "HI", "PET", "SPI", "SPEI", "UTCI"]
    clean = file_name.replace(".tif", "").replace("_cog", "")
    parts = clean.split('_')
    
    found_code, found_idx = None, -1

    if is_historical:
        if len(parts) > 5 and parts[5].upper() in codes:
            found_code = parts[5].upper()
            found_idx = 5
    else:
        for i in range(len(parts) - 1, -1, -1):
            if parts[i].upper() in codes:
                if parts[i].upper() == "TR" and i < 4: continue
                found_code = parts[i].upper()
                found_idx = i
                break
            
    if found_code:
        description = " ".join(parts[found_idx + 1:]).replace("_", " ").title()
        return f"{found_code} - {description}"
    
    return clean.replace("_", " ").title()

def get_stats_logic(file_name, stats_dict):
    """
    JSON'dan gerçek değerleri okur.
    """
    if not stats_dict: return 0.0, 100.0, ""
    
    if file_name in stats_dict:
        s = stats_dict[file_name]
        return float(s.get("min", 0)), float(s.get("max", 100)), s.get("unit", "")
                
    return 0.0, 100.0, ""

# --- SINGLE INDICE UI ---
@st.fragment
def render_single_indices_ui(available_dict, units_dict, stats, is_historical=False, prefix="one"):
    one_conf = {}
    selected_keys = []
    
    sorted_keys = sorted(available_dict.keys())
    
    for key in sorted_keys:
        filename = available_dict[key] if is_historical else key
        label = get_clean_name_logic(filename, is_historical)
        
        if st.checkbox(label, key=f"{prefix}_check_{filename}"):
            selected_keys.append(filename)
    
    if selected_keys:
        st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)
        thin_divider()
        for filename in selected_keys:
            label = get_clean_name_logic(filename, is_historical)
            
            with st.expander(label, expanded=True):
                d_min, d_max, d_unit = get_stats_logic(filename, stats)
                
                conf = {'visible': st.toggle("Visible on Map", value=True, key=f"vis_{prefix}_{filename}")}
                conf['unit'] = d_unit if d_unit else units_dict.get(filename, "")
                thin_divider()
                
                mode = st.radio("Mode", ["Interval", "Threshold"], key=f"mod_{prefix}_{filename}")
                conf['mode'] = mode
                
                if mode == "Interval":
                    # 1- Slider Control Switch (Default ON)
                    use_slider = st.toggle("Slider Control", value=True, key=f"use_sl_{prefix}_{filename}")
                    
                    if not use_slider:
                        col_min, col_max = st.columns(2)
                        v_min = col_min.number_input("Min", value=float(d_min), key=f"n_min_{prefix}_{filename}")
                        v_max = col_max.number_input("Max", value=float(d_max), key=f"n_max_{prefix}_{filename}")
                        conf['vmin'], conf['vmax'] = v_min, v_max
                    else:
                        # Sol tarafa Min, sağ tarafa Max (Daha yukarı kaydırıldı ve aralık açıldı)
                        st.markdown(
                            f'<div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: bold; margin-bottom: 10px; margin-top: 0px;">'
                            f'<span>Min</span><span>Max</span>'
                            f'</div>', 
                            unsafe_allow_html=True
                        )
                        
                        # Slider (Label gizli, CSS marjı sayesinde tooltip ile çakışmaz)
                        r = st.slider(
                            "Interval Slider", 
                            float(d_min), 
                            float(d_max), 
                            (float(d_min), float(d_max)), 
                            step=1.0, 
                            key=f"sl_{prefix}_{filename}",
                            label_visibility="collapsed" 
                        )
                        conf['vmin'], conf['vmax'] = r

                    thin_divider()

                    conf['sub_mode'] = st.selectbox("Figure Mode", ["Multi-Color", "One-Color"], key=f"sub_{prefix}_{filename}")
                    if conf['sub_mode'] == "Multi-Color":
                        # Palet seçenekleri artırıldı
                        palette_list = [
                            "RdYlBu_r", "Spectral_r", "viridis", "coolwarm", "magma", "plasma", "inferno", 
                            "terrain", "gist_earth", "cubehelix", "RdBu_r", "BrBG", "PRGn", "PiYG", 
                            "YlGnBu", "YlOrRd", "Blues", "Reds", "Greens", "Purples"
                        ]
                        conf['cmap'] = st.selectbox("Color Palette", palette_list, key=f"cp_{prefix}_{filename}")
                        gradient = np.linspace(0, 1, 256).reshape(1, -1); fig, ax = plt.subplots(figsize=(6, 0.18))
                        ax.imshow(gradient, aspect='auto', cmap=plt.get_cmap(conf['cmap']))
                        ax.set_axis_off(); st.pyplot(fig); plt.close(fig)
                        
                        col1, col2 = st.columns(2)
                        conf['ext_min'] = col1.checkbox("Extend Min", value=True, key=f"exmin_{prefix}_{filename}")
                        conf['ext_max'] = col2.checkbox("Extend Max", value=True, key=f"exmax_{prefix}_{filename}")
                        conf['disc'] = st.toggle("Discrete", value=True, key=f"ds_{prefix}_{filename}")
                        if conf['disc']: conf['lv'] = st.number_input("Levels", 2, 20, 10, key=f"lv_{prefix}_{filename}")
                    else:
                        conf['one_c'] = st.color_picker("Color", "#DC7933", key=f"c_{prefix}_{filename}")
                else:
                    # 1- Slider Control Switch (Default ON)
                    use_slider_th = st.toggle("Slider Control", value=True, key=f"use_sl_th_{prefix}_{filename}")
                    
                    init_val = float((d_min + d_max) / 2)
                    
                    if use_slider_th:
                        # 2- Threshold için de Min/Max etiketleri (Jilet gibi hizalı)
                        st.markdown(
                            f'<div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: bold; margin-bottom: 10px; margin-top: 0px;">'
                            f'<span>Min</span><span>Max</span>'
                            f'</div>', 
                            unsafe_allow_html=True
                        )
                        
                        th_val = st.slider(
                            "Threshold Slider", 
                            min_value=float(d_min), 
                            max_value=float(d_max), 
                            value=init_val, 
                            key=f"sl_th_{prefix}_{filename}",
                            label_visibility="collapsed" 
                        )
                    else:
                        th_val = st.number_input(
                            "Threshold Value", 
                            value=init_val, 
                            key=f"num_th_{prefix}_{filename}",
                            label_visibility="collapsed" 
                        )
                    
                    conf['thresh'] = th_val
                    
                    thin_divider()
                    
                    # Alt ve Üst Renk Seçenekleri (Lower / Higher)
                    col_b, col_a = st.columns(2)
                    conf['b_c'] = col_b.color_picker("Lower", "#4747B5", key=f"bc_{prefix}_{filename}")
                    conf['b_m'] = "Color" if not col_b.toggle("No Color", key=f"nb_{prefix}_{filename}") else "No Color"
                    
                    conf['a_c'] = col_a.color_picker("Higher", "#C93131", key=f"ac_{prefix}_{filename}")
                    conf['a_m'] = "Color" if not col_a.toggle("No Color ", key=f"na_{prefix}_{filename}") else "No Color"

                conf['alpha'] = st.slider("Opacity", 0.0, 1.0, 0.7, key=f"al_{prefix}_{filename}")
                one_conf[filename] = conf
    return selected_keys, one_conf

# --- MULTI INDICES UI ---
@st.fragment
def render_multi_indices_ui_fragment(av_hist, av_future, stats_h, stats_f):
    selected_meta = []
    
    with st.expander("CHELSA Historical (1995-2014)", expanded=False):
        for f_name, filename in sorted(av_hist.items()):
            label = get_clean_name_logic(filename, is_historical=True)
            if st.checkbox(label, key=f"m_h_{filename}"):
                selected_meta.append((filename, f"Hist: {label}", stats_h))
    
    with st.expander("CHELSA+GCMs Future", expanded=False):
        st.info("SSP126 (Empty)")
        with st.expander("SSP245", expanded=True):
            for period, label, prefix in [
                ("2041-2060", "Middle of the Century (2041-2060)", "SSP245 Mid: "), 
                ("2081-2100", "End of the Century (2081-2100)", "SSP245 End: ")
            ]:
                with st.expander(label, expanded=False):
                    f_data = [k for k in av_future.keys() if period in k]
                    for filename in sorted(f_data):
                        clean_label = get_clean_name_logic(filename, is_historical=False)
                        if st.checkbox(clean_label, key=f"m_{period}_{filename}"):
                            selected_meta.append((filename, f"{prefix}{clean_label}", stats_f))
        st.info("SSP585 (Empty)")

    all_sel_m, all_ind_conf = [], {}
    m_color, m_alpha = "#2FA42F", 0.8
    if selected_meta:
        st.markdown('<div style="margin-top: 25px;"></div>', unsafe_allow_html=True); thin_divider()
        for filename, leg_name, s_src in selected_meta:
            with st.expander(leg_name, expanded=True):
                m_min, m_max, _ = get_stats_logic(filename, s_src)
                
                # 1- Slider Control Switch (Default ON)
                use_slider_m = st.toggle("Slider Control", value=True, key=f"use_sl_m_{filename}")
                
                if use_slider_m:
                    # 2- "Range" kelimesi yerine Min/Max etiketleri (10px boşlukla)
                    st.markdown(
                        f'<div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: bold; margin-bottom: 10px; margin-top: 0px;">'
                        f'<span>Min</span><span>Max</span>'
                        f'</div>', 
                        unsafe_allow_html=True
                    )
                    
                    r = st.slider(
                        "Multi Range Slider", # Etiket gizli kalacak
                        float(m_min), 
                        float(m_max), 
                        (float(m_min), float(m_max)), 
                        key=f"rs_m_{filename}",
                        label_visibility="collapsed" 
                    )
                    v_min_final, v_max_final = r[0], r[1]
                else:
                    col1, col2 = st.columns(2)
                    v_min_final = col1.number_input("Min", value=float(m_min), key=f"n_min_m_{filename}")
                    v_max_final = col2.number_input("Max", value=float(m_max), key=f"n_max_m_{filename}")
                
                all_sel_m.append(filename)
                all_ind_conf[filename] = {'vmin': v_min_final, 'vmax': v_max_final, 'legend_name': leg_name}
        
        m_color = st.color_picker("Synthesis Color", "#2FA42F", key="m_g_cp")
        m_alpha = st.slider("Synthesis Opacity", 0.0, 1.0, 0.8, key="m_g_al")
    return all_sel_m, {'indices': all_ind_conf, 'color': m_color, 'alpha': m_alpha}

# --- ANA RENDER ---
def render_sidebar(av_hist, av_future, units_h, units_f, stats_h, stats_f):
    st.sidebar.title("Indices Map Tool")
    one_bundle, multi_bundle = ([], {}), ([], {})
    tab1, tab2 = st.sidebar.tabs(["Single-Indice", "Multi-Indices"])
    
    with tab1:
        sel_o, conf_o = [], {}
        with st.expander("CHELSA Historical (1995-2014)", expanded=False):
            s, c = render_single_indices_ui(av_hist, units_h, stats_h, is_historical=True, prefix="one_h")
            for k in c: c[k]['legend_prefix'] = "Hist: "
            sel_o.extend(s); conf_o.update(c)
        with st.expander("CHELSA+GCMs Future", expanded=False):
            st.info("SSP126 (Empty)")
            with st.expander("SSP245", expanded=True):
                for period, label, pre in [
                    ("2041-2060", "Middle of the Century (2041-2060)", "SSP245 Mid: "), 
                    ("2081-2100", "End of the Century (2081-2100)", "SSP245 End: ")
                ]:
                    with st.expander(label, expanded=False):
                        f_data_sidebar = {k: k for k in av_future.keys() if period in k}
                        s, c = render_single_indices_ui(f_data_sidebar, units_f, stats_f, is_historical=False, prefix=f"one_{period}")
                        for k in c: c[k]['legend_prefix'] = pre
                        sel_o.extend(s); conf_o.update(c)
            st.info("SSP585 (Empty)")
        one_bundle = (sel_o, conf_o)

    with tab2:
        multi_bundle = render_multi_indices_ui_fragment(av_hist, av_future, stats_h, stats_f)
    return one_bundle, multi_bundle