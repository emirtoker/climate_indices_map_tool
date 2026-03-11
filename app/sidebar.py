import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
import sys

# Maintain 'Agg' backend to ensure stability across hardware/online environments
matplotlib.use('Agg')

def render_sidebar(available_dict, data_objects=None, units_dict=None):
    st.sidebar.title("Indices Map Tool")
    st.sidebar.subheader("CHELSA Historical")
    
    if 'synthesis_active' not in st.session_state:
        st.session_state.synthesis_active = False

    tab1, tab2 = st.sidebar.tabs(["One-Indice", "Multi-Indices"])
    
    with tab1:
        sel_one = [k for k in sorted(available_dict.keys()) if st.checkbox(k, key=f"one_check_{k}")]
        one_conf = {}
        for name in sel_one:
            with st.expander(name, expanded=True):
                conf = {'visible': st.toggle("Visible on Map", value=True, key=f"vis_one_{name}")}
                
                # Dynamic range based on loaded data
                d_min = float(np.floor(data_objects[name].min())) if name in data_objects else 0.0
                d_max = float(np.ceil(data_objects[name].max())) if name in data_objects else 100.0
                conf['unit'] = units_dict.get(name, "")

                # Session State for synchronized Range Control
                if f"v_low_{name}" not in st.session_state:
                    st.session_state[f"v_low_{name}"] = d_min
                if f"v_high_{name}" not in st.session_state:
                    st.session_state[f"v_high_{name}"] = d_max

                mode = st.radio("Mode", ["Interval", "Threshold"], key=f"mod_one_{name}")
                conf['mode'] = mode
                
                if mode == "Interval":
                    st.markdown("**Range Control**")
                    
                    # 1. RANGE SLIDER (Synchronized with State)
                    r_v = st.slider(
                        "Select Range",
                        min_value=d_min,
                        max_value=d_max,
                        value=(st.session_state[f"v_low_{name}"], st.session_state[f"v_high_{name}"]),
                        step=1.0,
                        key=f"slider_{name}",
                        label_visibility="collapsed"
                    )
                    
                    # Update State from Slider
                    st.session_state[f"v_low_{name}"] = r_v[0]
                    st.session_state[f"v_high_{name}"] = r_v[1]

                    # 2. NUMERIC INPUTS (Synchronized with Slider)
                    c1_in, c2_in = st.columns(2)
                    with c1_in:
                        v_min_input = st.number_input(
                            "Min Value", 
                            min_value=d_min, 
                            max_value=d_max, 
                            value=st.session_state[f"v_low_{name}"],
                            key=f"nmin_one_{name}"
                        )
                        # Trigger rerun on direct input change
                        if v_min_input != st.session_state[f"v_low_{name}"]:
                            st.session_state[f"v_low_{name}"] = v_min_input
                            st.rerun()

                    with c2_in:
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

                    # 3. FIGURE MODE
                    sub = st.selectbox("Figure Mode", ["Multi-Color", "One-Color"], key=f"sub_one_{name}")
                    conf['sub_mode'] = sub
                    
                    if sub == "Multi-Color":
                        conf['cmap'] = st.selectbox("Color Palette", ["Spectral_r", "RdYlBu_r", "viridis", "magma", "YlOrRd", "Reds", "Blues"], key=f"cp_one_{name}")
                        
                        # --- THIN, ELEGANT COLOR PALETTE PREVIEW (FIXED SPINE THICKNESS) ---
                        gradient = np.linspace(0, 1, 256).reshape(1, -1)
                        fig, ax = plt.subplots(figsize=(6, 0.12)) # Elegant slim height
                        ax.imshow(gradient, aspect='auto', cmap=plt.get_cmap(conf['cmap']))
                        
                        # Customize spines (the border around the colorbar)
                        # Setting linewidth to 0.5 (half of standard) and lightgrey
                        for spine in ax.spines.values():
                            spine.set_linewidth(0.5)
                            spine.set_color('lightgrey')
                        
                        # Remove ticks and labels but keep spines
                        ax.set_xticks([])
                        ax.set_yticks([])
                        ax.set_xticklabels([])
                        ax.set_yticklabels([])
                        
                        st.pyplot(fig)
                        # Remove from memory immediately
                        plt.close(fig)
                        
                        # 4. EXTEND CHECKBOXES
                        c1, c2 = st.columns(2)
                        with c1:
                            conf['ext_min'] = st.checkbox("Extend Min", value=True, key=f"exmin_one_{name}")
                        with c2:
                            conf['ext_max'] = st.checkbox("Extend Max", value=True, key=f"exmax_one_{name}")
                        
                        conf['disc'] = st.toggle("Discrete Values", value=True, key=f"ds_one_{name}")
                        if conf['disc']: 
                            conf['lv'] = st.number_input("Levels", 2, 20, 10, key=f"lv_one_{name}")
                    else:
                        conf['one_c'] = st.color_picker("Pick Color", "#FF0000", key=f"c_one_{name}")
                
                else:
                    conf['thresh'] = st.number_input("Threshold Value", value=float((d_min+d_max)/2), key=f"th_one_{name}")
                    col_b, col_a = st.columns(2)
                    with col_b:
                        conf['b_c'] = st.color_picker("Color Below", "#0000FF", key=f"bc_one_{name}")
                        conf['b_m'] = "No Color" if st.toggle("No Color (B)", key=f"no_b_{name}") else "Color"
                    with col_a:
                        conf['a_c'] = st.color_picker("Color Above", "#FF0000", key=f"ac_one_{name}")
                        conf['a_m'] = "No Color" if st.toggle("No Color (A)", key=f"no_a_{name}") else "Color"

                conf['alpha'] = st.slider("Opacity", 0.0, 1.0, 0.7, key=f"al_one_{name}")
                one_conf[name] = conf

    # Multi-Indices Tab (Değişmedi)
    with tab2:
        sel_multi = [k for k in sorted(available_dict.keys()) if st.checkbox(k, key=f"multi_check_{k}")]
        multi_conf = {'indices': {}}
        if sel_multi:
            st.divider()
            for name in sel_multi:
                with st.expander(f"Synthesis: {name}", expanded=True):
                    d_min_m = float(np.floor(data_objects[name].min())) if name in data_objects else 0.0
                    d_max_m = float(np.ceil(data_objects[name].max())) if name in data_objects else 100.0
                    r_v_m = st.slider("Range", d_min_m, d_max_m, (d_min_m, d_max_m), step=1.0, key=f"rs_multi_{name}")
                    multi_conf['indices'][name] = {'vmin': r_v_m[0], 'vmax': r_v_m[1]}
            
            multi_conf['color'] = st.color_picker("Synthesis Color", "#00FF00", key="m_g_c")
            multi_conf['alpha'] = st.slider("Synthesis Opacity", 0.0, 1.0, 0.8, key="m_g_al")
            
            if st.button("Calculate Intersection", use_container_width=True):
                st.session_state.synthesis_active = True
            if st.session_state.get('synthesis_active'):
                if st.button("Reset Synthesis", use_container_width=True):
                    st.session_state.synthesis_active = False
                    st.rerun()

    return (sel_one, one_conf), (sel_multi, multi_conf)