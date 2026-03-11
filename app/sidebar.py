import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
import matplotlib
import sys

# Use 'Agg' backend to prevent memory/hardware conflicts on different OS environments
matplotlib.use('Agg')

def render_sidebar(available_dict, data_objects=None, units_dict=None):
    """
    Renders the Streamlit sidebar for index selection and visualization configuration.
    Features synchronized range controls and dynamic colormap previews.
    """
    st.sidebar.title("Indices Map Tool")
    st.sidebar.subheader("CHELSA Historical")
    
    # Initialize synthesis state if not present
    if 'synthesis_active' not in st.session_state:
        st.session_state.synthesis_active = False

    # Primary navigation tabs
    tab1, tab2 = st.sidebar.tabs(["Single Index", "Multi-Indices"])
    
    # --- TAB 1: SINGLE INDEX CONFIGURATION ---
    with tab1:
        selected_indices = [k for k in sorted(available_dict.keys()) if st.checkbox(k, key=f"one_check_{k}")]
        one_conf = {}
        
        for name in selected_indices:
            with st.expander(name, expanded=True):
                conf = {'visible': st.toggle("Visible on Map", value=True, key=f"vis_one_{name}")}
                
                # Establish dynamic range boundaries from dataset
                d_min = float(np.floor(data_objects[name].min())) if name in data_objects else 0.0
                d_max = float(np.ceil(data_objects[name].max())) if name in data_objects else 100.0
                conf['unit'] = units_dict.get(name, "")

                # Synchronize Range Control via Session State
                if f"v_low_{name}" not in st.session_state:
                    st.session_state[f"v_low_{name}"] = d_min
                if f"v_high_{name}" not in st.session_state:
                    st.session_state[f"v_high_{name}"] = d_max

                mode = st.radio("Visualization Mode", ["Interval", "Threshold"], key=f"mod_one_{name}")
                conf['mode'] = mode
                
                if mode == "Interval":
                    st.markdown("**Range Control**")
                    
                    # 1. RANGE SLIDER (State-linked)
                    range_values = st.slider(
                        "Select Data Range",
                        min_value=d_min,
                        max_value=d_max,
                        value=(st.session_state[f"v_low_{name}"], st.session_state[f"v_high_{name}"]),
                        step=1.0,
                        key=f"slider_{name}",
                        label_visibility="collapsed"
                    )
                    
                    # Update state variables
                    st.session_state[f"v_low_{name}"] = range_values[0]
                    st.session_state[f"v_high_{name}"] = range_values[1]

                    # 2. NUMERIC INPUTS (Bi-directional sync with slider)
                    col1_input, col2_input = st.columns(2)
                    with col1_input:
                        v_min_input = st.number_input(
                            "Min Value", 
                            min_value=d_min, 
                            max_value=d_max, 
                            value=st.session_state[f"v_low_{name}"],
                            key=f"nmin_one_{name}"
                        )
                        if v_min_input != st.session_state[f"v_low_{name}"]:
                            st.session_state[f"v_low_{name}"] = v_min_input
                            st.rerun()

                    with col2_input:
                        v_max_input = st.number_input(
                            "Max Value", 
                            min_value=d_min, 
                            max_value=d_max, 
                            value=st.session_state[f"v_high_{name}"],
                            key=f"nmax_one_{name}"
                        )
                        if v_max_input != st.session_state[f"v_high_{name}"]:
                            st.session_state[f"v_high_{name}"] = v_max_input
                            st.rerun()

                    conf['vmin'] = st.session_state[f"v_low_{name}"]
                    conf['vmax'] = st.session_state[f"v_high_{name}"]

                    # 3. COLOR RENDERING OPTIONS
                    sub_mode = st.selectbox("Color Mode", ["Multi-Color", "One-Color"], key=f"sub_one_{name}")
                    conf['sub_mode'] = sub_mode
                    
                    if sub_mode == "Multi-Color":
                        conf['cmap'] = st.selectbox("Color Palette", ["Spectral_r", "RdYlBu_r", "viridis", "magma", "YlOrRd", "Reds", "Blues"], key=f"cp_one_{name}")
                        
                        # --- ELEGANT COLORBAR PREVIEW ---
                        gradient = np.linspace(0, 1, 256).reshape(1, -1)
                        fig, ax = plt.subplots(figsize=(6, 0.12))
                        ax.imshow(gradient, aspect='auto', cmap=plt.get_cmap(conf['cmap']))
                        
                        # Minimalist borders (spines)
                        for spine in ax.spines.values():
                            spine.set_linewidth(0.5)
                            spine.set_color('lightgrey')
                        
                        ax.set_xticks([])
                        ax.set_yticks([])
                        st.pyplot(fig)
                        plt.close(fig) # Immediate memory cleanup
                        
                        # 4. SPATIAL CLIPPING (EXTEND)
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
                    # Threshold Logic for binary classification
                    conf['thresh'] = st.number_input("Threshold Value", value=float((d_min+d_max)/2), key=f"th_one_{name}")
                    col_below, col_above = st.columns(2)
                    with col_below:
                        conf['b_c'] = st.color_picker("Below Color", "#0000FF", key=f"bc_one_{name}")
                        no_color_below = st.toggle("Transparent (B)", key=f"no_b_{name}")
                        conf['b_m'] = "No Color" if no_color_below else "Color"
                    with col_above:
                        conf['a_c'] = st.color_picker("Above Color", "#FF0000", key=f"ac_one_{name}")
                        no_color_above = st.toggle("Transparent (A)", key=f"no_a_{name}")
                        conf['a_m'] = "No Color" if no_color_above else "Color"

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
            
            multi_conf['color'] = st.color_picker("Synthesis Result Color", "#00FF00", key="m_g_c")
            multi_conf['alpha'] = st.slider("Synthesis Opacity", 0.0, 1.0, 0.8, key="m_g_al")
            
            if st.button("Generate Intersection", use_container_width=True):
                st.session_state.synthesis_active = True
            
            if st.session_state.get('synthesis_active'):
                if st.button("Clear Results", use_container_width=True):
                    st.session_state.synthesis_active = False
                    st.rerun()

    return (selected_indices, one_conf), (selected_multi, multi_conf)