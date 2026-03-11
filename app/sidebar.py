import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
import matplotlib
import sys

# Professional hardware-safe backend to prevent memory conflicts
matplotlib.use('Agg')

def render_sidebar(available_dict, data_objects=None, units_dict=None):
    """
    Streamlined sidebar for climate index configuration.
    Controlled exclusively via Range Sliders to ensure stability and prevent refresh loops.
    """
    st.sidebar.title("Indices Map Tool")
    st.sidebar.subheader("CHELSA Historical")
    
    if 'synthesis_active' not in st.session_state:
        st.session_state.synthesis_active = False

    tab1, tab2 = st.sidebar.tabs(["Single Index", "Multi-Indices"])
    
    # --- TAB 1: SINGLE INDEX CONFIGURATION ---
    with tab1:
        selected_indices = [k for k in sorted(available_dict.keys()) if st.checkbox(k, key=f"one_check_{k}")]
        one_conf = {}
        
        for name in selected_indices:
            with st.expander(name, expanded=True):
                conf = {'visible': st.toggle("Visible on Map", value=True, key=f"vis_one_{name}")}
                
                # Dynamic boundaries derived from the specific dataset
                d_min = float(np.floor(data_objects[name].min())) if name in data_objects else 0.0
                d_max = float(np.ceil(data_objects[name].max())) if name in data_objects else 100.0
                conf['unit'] = units_dict.get(name, "")

                mode = st.radio("Visualization Mode", ["Interval", "Threshold"], key=f"mod_one_{name}")
                conf['mode'] = mode
                
                if mode == "Interval":
                    st.markdown("**Range Control**")
                    
                    # SINGLE CONTROL POINT: Range Slider
                    # This slider now acts as the sole input for vmin and vmax
                    range_values = st.slider(
                        "Define Active Range",
                        min_value=d_min,
                        max_value=d_max,
                        value=(d_min, d_max), # Default to full range
                        step=1.0,
                        key=f"slider_only_{name}"
                    )
                    
                    conf['vmin'] = range_values[0]
                    conf['vmax'] = range_values[1]

                    # Visual display of the selected values for user clarity
                    st.caption(f"Selected: {conf['vmin']:.0f} to {conf['vmax']:.0f} {conf['unit']}")

                    # FIGURE MODE & COLOR ENGINE
                    sub_mode = st.selectbox("Color Mode", ["Multi-Color", "One-Color"], key=f"sub_one_{name}")
                    conf['sub_mode'] = sub_mode
                    
                    if sub_mode == "Multi-Color":
                        conf['cmap'] = st.selectbox("Color Palette", ["Spectral_r", "RdYlBu_r", "viridis", "magma", "YlOrRd", "Reds", "Blues"], key=f"cp_one_{name}")
                        
                        # --- ELEGANT SLIM COLORBAR PREVIEW ---
                        gradient = np.linspace(0, 1, 256).reshape(1, -1)
                        fig, ax = plt.subplots(figsize=(6, 0.12))
                        ax.imshow(gradient, aspect='auto', cmap=plt.get_cmap(conf['cmap']))
                        
                        # Professional minimalist spines
                        for spine in ax.spines.values():
                            spine.set_linewidth(0.5)
                            spine.set_color('lightgrey')
                        
                        ax.set_xticks([]); ax.set_yticks([])
                        st.pyplot(fig)
                        plt.close(fig) # Immediate memory cleanup
                        
                        # SPATIAL CLIPPING CONTROLS
                        col_ext1, col_ext2 = st.columns(2)
                        with col_ext1:
                            conf['ext_min'] = st.checkbox("Extend Min", value=True, key=f"exmin_one_{name}")
                        with col_ext2:
                            conf['ext_max'] = st.checkbox("Extend Max", value=True, key=f"exmax_one_{name}")
                        
                        conf['disc'] = st.toggle("Discrete Levels", value=True, key=f"ds_one_{name}")
                        if conf['disc']: 
                            conf['lv'] = st.number_input("Levels", 2, 20, 10, key=f"lv_one_{name}")
                    else:
                        conf['one_c'] = st.color_picker("Layer Color", "#FF0000", key=f"c_one_{name}")
                
                else:
                    # Threshold Logic (Binary Classification)
                    conf['thresh'] = st.number_input("Threshold Value", value=float((d_min+d_max)/2), key=f"th_one_{name}")
                    col_b, col_a = st.columns(2)
                    with col_b:
                        conf['b_c'] = st.color_picker("Below Color", "#0000FF", key=f"bc_one_{name}")
                        conf['b_m'] = "No Color" if st.toggle("Transparent (B)", key=f"no_b_{name}") else "Color"
                    with col_a:
                        conf['a_c'] = st.color_picker("Above Color", "#FF0000", key=f"ac_one_{name}")
                        conf['a_m'] = "No Color" if st.toggle("Transparent (A)", key=f"no_a_{name}") else "Color"

                conf['alpha'] = st.slider("Opacity", 0.0, 1.0, 0.7, key=f"al_one_{name}")
                one_conf[name] = conf

    # --- TAB 2: MULTI-INDICES (SYNTHESIS) ---
    with tab2:
        selected_multi = [k for k in sorted(available_dict.keys()) if st.checkbox(k, key=f"multi_check_{k}")]
        multi_conf = {'indices': {}}
        
        if selected_multi:
            st.divider()
            for name in selected_multi:
                with st.expander(f"Criteria: {name}", expanded=True):
                    d_min_m = float(np.floor(data_objects[name].min())) if name in data_objects else 0.0
                    d_max_m = float(np.ceil(data_objects[name].max())) if name in data_objects else 100.0
                    m_range = st.slider("Active Range", d_min_m, d_max_m, (d_min_m, d_max_m), step=1.0, key=f"rs_multi_{name}")
                    multi_conf['indices'][name] = {'vmin': m_range[0], 'vmax': m_range[1]}
            
            multi_conf['color'] = st.color_picker("Synthesis Color", "#00FF00", key="m_g_c")
            multi_conf['alpha'] = st.slider("Synthesis Opacity", 0.0, 1.0, 0.8, key="m_g_al")
            
            if st.button("Generate Intersection", use_container_width=True):
                st.session_state.synthesis_active = True
            
            if st.session_state.get('synthesis_active'):
                if st.button("Reset Synthesis", use_container_width=True):
                    st.session_state.synthesis_active = False
                    st.rerun()

    return (selected_indices, one_conf), (selected_multi, multi_conf)