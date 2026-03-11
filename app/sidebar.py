import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
import matplotlib
import sys

matplotlib.use('Agg')

def render_sidebar(available_dict, data_objects=None, units_dict=None):
    DIVIDER_COLOR = "#888a8d"
    LABEL_STYLE = '<p style="font-size: 14px; color: #eeeeee; margin-bottom: 2px; font-weight: 400;">'

    def thin_divider():
        st.markdown(f'<hr style="border: none; border-top: 1.5px solid {DIVIDER_COLOR}; margin: 2px 0 12px 0;">', unsafe_allow_html=True)

    st.sidebar.title("Indices Map Tool")
    st.sidebar.subheader("CHELSA Historical")
    
    if 'synthesis_active' not in st.session_state:
        st.session_state.synthesis_active = False

    tab1, tab2 = st.sidebar.tabs(["Single-Indice", "Multi-Indices"])
    
    with tab1:
        selected_indices = [k for k in sorted(available_dict.keys()) if st.checkbox(k, key=f"one_check_{k}")]
        one_conf = {}
        
        for name in selected_indices:
            with st.expander(name, expanded=True):
                conf = {'visible': st.toggle("Visible on Map", value=True, key=f"vis_one_{name}")}
                thin_divider()
                
                d_min = float(np.floor(data_objects[name].min())) if name in data_objects else 0.0
                d_max = float(np.ceil(data_objects[name].max())) if name in data_objects else 100.0
                conf['unit'] = units_dict.get(name, "")

                mode = st.radio("Mode", ["Interval", "Threshold"], key=f"mod_one_{name}")
                conf['mode'] = mode
                thin_divider()
                
                if mode == "Interval":
                    use_slider = st.session_state.get(f"use_sl_{name}", False)
                    if not use_slider:
                        col_min, col_max = st.columns(2)
                        with col_min:
                            v_min = st.number_input("Min", value=d_min, key=f"num_min_{name}")
                        with col_max:
                            v_max = st.number_input("Max", value=d_max, key=f"num_max_{name}")
                        st.toggle("Slider Control", value=False, key=f"use_sl_{name}")
                        conf['vmin'], conf['vmax'] = v_min, v_max
                    else:
                        st.toggle("Slider Control", value=True, key=f"use_sl_{name}")
                        range_values = st.slider("Range Selector", d_min, d_max, (d_min, d_max), step=1.0, key=f"sl_bar_{name}", label_visibility="collapsed")
                        conf['vmin'], conf['vmax'] = range_values

                    thin_divider()
                    sub_mode = st.selectbox("Figure Mode", ["Multi-Color", "One-Color"], key=f"sub_one_{name}")
                    conf['sub_mode'] = sub_mode
                    
                    if sub_mode == "Multi-Color":
                        conf['cmap'] = st.selectbox("Color Palette", ["Spectral_r", "RdYlBu_r", "viridis", "magma", "YlOrRd", "Reds", "Blues"], key=f"cp_one_{name}")
                        gradient = np.linspace(0, 1, 256).reshape(1, -1)
                        fig, ax = plt.subplots(figsize=(6, 0.18)) 
                        ax.imshow(gradient, aspect='auto', cmap=plt.get_cmap(conf['cmap']))
                        for spine in ax.spines.values():
                            spine.set_linewidth(0.3); spine.set_color('lightgrey')
                        ax.set_xticks([]); ax.set_yticks([])
                        st.pyplot(fig); plt.close(fig)
                        
                        col_ext1, col_ext2 = st.columns(2)
                        with col_ext1: conf['ext_min'] = st.checkbox("Extend Min", value=True, key=f"exmin_one_{name}")
                        with col_ext2: conf['ext_max'] = st.checkbox("Extend Max", value=True, key=f"exmax_one_{name}")
                        
                        thin_divider()
                        conf['disc'] = st.toggle("Discrete Values", value=True, key=f"ds_one_{name}")
                        if conf['disc']: 
                            conf['lv'] = st.number_input("Levels", 2, 20, 10, key=f"lv_one_{name}")
                    else:
                        conf['one_c'] = st.color_picker("Color", "#DC7933", key=f"c_one_{name}")
                
                else:
                    use_th_slider = st.session_state.get(f"use_th_sl_{name}", False)
                    default_th = float((d_min+d_max)/2)
                    
                    if not use_th_slider:
                        conf['thresh'] = st.number_input("Threshold Value", value=default_th, key=f"th_val_{name}")
                        st.toggle("Slider Control", value=False, key=f"use_th_sl_{name}")
                    else:
                        st.markdown(f'{LABEL_STYLE}Threshold Value</p>', unsafe_allow_html=True)
                        conf['thresh'] = st.slider("Threshold Selector", d_min, d_max, default_th, step=0.1, key=f"th_sl_{name}", label_visibility="collapsed")
                        st.toggle("Slider Control", value=True, key=f"use_th_sl_{name}")
                    
                    thin_divider()
                    col_b, col_a = st.columns(2)
                    with col_b:
                        conf['b_c'] = st.color_picker("Below", "#4747B5", key=f"bc_one_{name}")
                        conf['b_m'] = "No Color" if st.toggle("No Color", key=f"no_b_{name}") else "Color"
                    with col_a:
                        conf['a_c'] = st.color_picker("Above", "#C93131", key=f"ac_one_{name}")
                        conf['a_m'] = "No Color" if st.toggle("No Color ", key=f"no_a_{name}") else "Color"

                thin_divider()
                st.markdown(f'{LABEL_STYLE}Opacity</p>', unsafe_allow_html=True)
                conf['alpha'] = st.slider("Opacity Slider", 0.0, 1.0, 0.7, key=f"al_one_{name}", label_visibility="collapsed")
                one_conf[name] = conf

    with tab2:
        selected_multi = [k for k in sorted(available_dict.keys()) if st.checkbox(k, key=f"multi_check_{k}")]
        multi_conf = {'indices': {}}
        if selected_multi:
            st.divider()
            for name in selected_multi:
                with st.expander(f"Criteria: {name}", expanded=True):
                    d_min_m = float(np.floor(data_objects[name].min())) if name in data_objects else 0.0
                    d_max_m = float(np.ceil(data_objects[name].max())) if name in data_objects else 100.0
                    m_range = st.slider("Range", d_min_m, d_max_m, (d_min_m, d_max_m), step=1.0, key=f"rs_multi_{name}")
                    multi_conf['indices'][name] = {'vmin': m_range[0], 'vmax': m_range[1]}
            
            multi_conf['color'] = st.color_picker("Color", "#2FA42F", key="m_g_c")
            multi_conf['alpha'] = st.slider("Opacity", 0.0, 1.0, 0.8, key="m_g_al")
            
            if st.button("Generate Intersection", use_container_width=True):
                st.session_state.synthesis_active = True
            if st.session_state.get('synthesis_active'):
                if st.button("Reset Results", use_container_width=True):
                    st.session_state.synthesis_active = False; st.rerun()

    return (selected_indices, one_conf), (selected_multi, multi_conf)