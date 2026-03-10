import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

def render_sidebar(available_dict, data_objects=None, units_dict=None):
    st.sidebar.title("Indices Map Tool")
    st.sidebar.subheader("CHELSA Historical")
    
    if 'synthesis_active' not in st.session_state:
        st.session_state.synthesis_active = False

    tab1, tab2 = st.sidebar.tabs(["One-Indice", "Multi-Indices"])
    
    # --- TAB 1: ONE-INDICE ---
    with tab1:
        sel_one = [k for k in sorted(available_dict.keys()) if st.checkbox(k, key=f"one_check_{k}")]
        one_conf = {}
        for name in sel_one:
            with st.expander(name, expanded=True):
                conf = {'visible': st.toggle("Visible on Map", value=True, key=f"vis_one_{name}")}
                
                # Calculate data range
                d_min = int(np.floor(data_objects[name].min())) if name in data_objects else 0
                d_max = int(np.ceil(data_objects[name].max())) if name in data_objects else 100
                conf['unit'] = units_dict.get(name, "")
                
                mode = st.radio("Mode", ["Interval", "Threshold"], key=f"mod_one_{name}")
                conf['mode'] = mode
                
                if mode == "Interval":
                    # Changed label to Figure Mode
                    sub = st.selectbox("Figure Mode", ["Multi-Color", "One-Color"], key=f"sub_one_{name}")
                    conf['sub_mode'] = sub
                    
                    if sub == "Multi-Color":
                        # Changed label to Color Palette
                        conf['cmap'] = st.selectbox("Color Palette", ["Spectral_r", "RdYlBu_r", "viridis", "magma", "YlOrRd", "Reds", "Blues"], key=f"cp_one_{name}")
                        
                        # Render thinner, elegant color palette preview
                        gradient = np.linspace(0, 1, 256).reshape(1, -1)
                        fig, ax = plt.subplots(figsize=(6, 0.15)) # Height reduced for elegance
                        ax.imshow(gradient, aspect='auto', cmap=plt.get_cmap(conf['cmap']))
                        ax.set_axis_off()
                        st.pyplot(fig)
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            conf['vmin'] = st.number_input("Min", value=float(d_min), key=f"nmin_one_{name}")
                            conf['ext_min'] = st.checkbox("Extend Min", key=f"exmin_one_{name}")
                        with c2:
                            conf['vmax'] = st.number_input("Max", value=float(d_max), key=f"nmax_one_{name}")
                            conf['ext_max'] = st.checkbox("Extend Max", key=f"exmax_one_{name}")
                        
                        conf['disc'] = st.toggle("Discrete Values", value=True, key=f"ds_one_{name}")
                        if conf['disc']: 
                            conf['lv'] = st.number_input("Levels", 2, 20, 10, key=f"lv_one_{name}")
                    else:
                        conf['one_c'] = st.color_picker("Color", "#FF0000", key=f"c_one_{name}")
                        # Simplified label to Range
                        r_v = st.slider("Range", d_min, d_max, (d_min, d_max), step=1, key=f"rs_one_{name}")
                        conf['vmin'], conf['vmax'] = r_v[0], r_v[1]
                else:
                    conf['thresh'] = st.number_input("Threshold Value", value=float((d_min+d_max)/2), key=f"th_one_{name}")
                    
                    col_b, col_a = st.columns(2)
                    with col_b:
                        st.markdown("**Below**")
                        # Simplified label to Color
                        conf['b_c'] = st.color_picker("Color", "#0000FF", key=f"bc_one_{name}")
                        no_color_b = st.toggle("No Color", value=False, key=f"no_b_{name}")
                        conf['b_m'] = "No Color" if no_color_b else "Color"
                    
                    with col_a:
                        st.markdown("**Above**")
                        conf['a_c'] = st.color_picker("Color", "#FF0000", key=f"ac_one_{name}")
                        no_color_a = st.toggle("No Color", value=False, key=f"no_a_{name}")
                        conf['a_m'] = "No Color" if no_color_a else "Color"

                conf['alpha'] = st.slider("Opacity", 0.0, 1.0, 0.7, key=f"al_one_{name}")
                one_conf[name] = conf

    # --- TAB 2: MULTI-INDICES ---
    with tab2:
        sel_multi = [k for k in sorted(available_dict.keys()) if st.checkbox(k, key=f"multi_check_{k}")]
        multi_conf = {'indices': {}}
        if sel_multi:
            st.divider()
            for name in sel_multi:
                with st.expander(f"Interval: {name}", expanded=True):
                    d_min = int(np.floor(data_objects[name].min())) if name in data_objects else 0
                    d_max = int(np.ceil(data_objects[name].max())) if name in data_objects else 100
                    # Simplified label to Range
                    r_v = st.slider("Range", d_min, d_max, (d_min, d_max), step=1, key=f"rs_multi_{name}")
                    multi_conf['indices'][name] = {'vmin': r_v[0], 'vmax': r_v[1]}
            
            multi_conf['color'] = st.color_picker("Synthesis Color", "#00FF00", key="m_g_c")
            multi_conf['alpha'] = st.slider("Synthesis Opacity", 0.0, 1.0, 0.8, key="m_g_al")
            
            if st.button("Find Intersection", use_container_width=True):
                st.session_state.synthesis_active = True
            
            if st.session_state.get('synthesis_active'):
                if st.button("Clear Synthesis", use_container_width=True):
                    st.session_state.synthesis_active = False
                    st.rerun()

    return (sel_one, one_conf), (sel_multi, multi_conf)