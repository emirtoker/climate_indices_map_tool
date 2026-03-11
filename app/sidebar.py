import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
import matplotlib
import sys

# Professional hardware-safe backend
matplotlib.use('Agg')

def render_sidebar(available_dict, data_objects=None, units_dict=None):
    """
    Minimalist sidebar for climate index configuration.
    Simplified UI focusing on essential controls.
    """
    st.sidebar.title("Indices Map Tool")
    st.sidebar.subheader("CHELSA Historical")
    
    if 'synthesis_active' not in st.session_state:
        st.session_state.synthesis_active = False

    tab1, tab2 = st.sidebar.tabs(["Single Index", "Multi-Indices"])
    
    # --- TAB 1: SINGLE INDEX ---
    with tab1:
        selected_indices = [k for k in sorted(available_dict.keys()) if st.checkbox(k, key=f"one_check_{k}")]
        one_conf = {}
        
        for name in selected_indices:
            with st.expander(name, expanded=True):
                conf = {'visible': st.toggle("Visible on Map", value=True, key=f"vis_one_{name}")}
                
                # Dynamic boundaries
                d_min = float(np.floor(data_objects[name].min())) if name in data_objects else 0.0
                d_max = float(np.ceil(data_objects[name].max())) if name in data_objects else 100.0
                conf['unit'] = units_dict.get(name, "")

                mode = st.radio("Mode", ["Interval", "Threshold"], key=f"mod_one_{name}")
                conf['mode'] = mode
                
                if mode == "Interval":
                    # Minimalist Range Control
                    st.write("Range")
                    range_values = st.slider(
                        "Range",
                        min_value=d_min,
                        max_value=d_max,
                        value=(d_min, d_max),
                        step=1.0,
                        key=f"slider_only_{name}",
                        label_visibility="collapsed"
                    )
                    
                    conf['vmin'] = range_values[0]
                    conf['vmax'] = range_values[1]

                    # Figure Mode Configuration
                    sub_mode = st.selectbox("Figure Mode", ["Multi-Color", "One-Color"], key=f"sub_one_{name}")
                    conf['sub_mode'] = sub_mode
                    
                    if sub_mode == "Multi-Color":
                        conf['cmap'] = st.selectbox("Color Palette", ["Spectral_r", "RdYlBu_r", "viridis", "magma", "YlOrRd", "Reds", "Blues"], key=f"cp_one_{name}")
                        
                        # Elegant slim colorbar preview
                        gradient = np.linspace(0, 1, 256).reshape(1, -1)
                        fig, ax = plt.subplots(figsize=(6, 0.12))
                        ax.imshow(gradient, aspect='auto', cmap=plt.get_cmap(conf['cmap']))
                        
                        # Ultra-thin minimalist spines
                        for spine in ax.spines.values():
                            spine.set_linewidth(0.5)
                            spine.set_color('lightgrey')
                        
                        ax.set_xticks([]); ax.set_yticks([])
                        st.pyplot(fig)
                        plt.close(fig)
                        
                        # Clipping (Extend)
                        c_ext1, c_ext2 = st.columns(2)
                        with c_ext1:
                            conf['ext_min'] = st.checkbox("Extend Min", value=True, key=f"exmin_one_{name}")
                        with c_ext2:
                            conf['ext_max'] = st.checkbox("Extend Max", value=True, key=f"exmax_one_{name}")
                        
                        conf['disc'] = st.toggle("Discrete Values", value=True, key=f"ds_one_{name}")
                        if conf['disc']: 
                            conf['lv'] = st.number_input("Levels", 2, 20, 10, key=f"lv_one_{name}")
                    else:
                        conf['one_c'] = st.color_picker("Color", "#FF0000", key=f"c_one_{name}")
                
                else:
                    # Threshold Logic
                    conf['thresh'] = st.number_input("Threshold Value", value=float((d_min+d_max)/2), key=f"th_one_{name}")
                    col_b, col_a = st.columns(2)
                    with col_b:
                        conf['b_c'] = st.color_picker("Below", "#0000FF", key=f"bc_one_{name}")
                        conf['b_m'] = "No Color" if st.toggle("No Color (B)", key=f"no_b_{name}") else "Color"
                    with col_a:
                        conf['a_c'] = st.color_picker("Above", "#FF0000", key=f"ac_one_{name}")
                        conf['a_m'] = "No Color" if st.toggle("No Color (A)", key=f"no_a_{name}") else "Color"

                conf['alpha'] = st.slider("Opacity", 0.0, 1.0, 0.7, key=f"al_one_{name}")
                one_conf[name] = conf

    # --- TAB 2: MULTI-INDICES ---
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
            
            multi_conf['color'] = st.color_picker("Synthesis Color", "#00FF00", key="m_g_c")
            multi_conf['alpha'] = st.slider("Synthesis Opacity", 0.0, 1.0, 0.8, key="m_g_al")
            
            if st.button("Generate Intersection", use_container_width=True):
                st.session_state.synthesis_active = True
            
            if st.session_state.get('synthesis_active'):
                if st.button("Reset Results", use_container_width=True):
                    st.session_state.synthesis_active = False
                    st.rerun()

    return (selected_indices, one_conf), (selected_multi, multi_conf)