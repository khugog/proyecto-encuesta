import streamlit as st

def render_question_builder_fields(q_id, prefix="", default_texto="", default_tipo="Texto libre", default_opciones=None):
    if default_opciones is None:
        default_opciones = []
        
    pref = f"_{prefix}" if prefix else ""
    
    k_texto = f"texto{pref}_{q_id}"
    if k_texto not in st.session_state:
        st.session_state[k_texto] = default_texto
    
    def _sync_texto():
        # Streamlit actualiza la key del widget antes de llamar on_change,
        # así cualquier clic posterior al callback leerá el valor actualizado.
        pass  # La key ya está actualizada en session_state automáticamente
        
    texto = st.text_input(
        "Escribe la pregunta:",
        key=k_texto,
        placeholder="Ej. ¿Cuál es tu color favorito?",
        on_change=_sync_texto
    )
    
    k_tipo = f"tipo{pref}_{q_id}"
    if k_tipo not in st.session_state:
        st.session_state[k_tipo] = default_tipo

    # ⚡ Añadimos "Escala Likert (Caritas)" a la lista
    tipos_disp = [
        "Texto libre", 
        "Opción única", 
        "Opción múltiple", 
        "Escala Likert", 
        "Escala Likert (Caritas)", # <-- Nueva opción
        "NPS"
    ]
    tipo = st.selectbox("Formato de respuesta:", tipos_disp, key=k_tipo)
    
    opciones = []
    
    # ⚡ Mantenemos la lógica de opciones para única y múltiple
    if tipo in ["Opción única", "Opción múltiple"]:
        if f"opciones{pref}_{q_id}" not in st.session_state:
            st.session_state[f"opciones{pref}_{q_id}"] = default_opciones.copy()
        if f"op_counter{pref}_{q_id}" not in st.session_state:
            st.session_state[f"op_counter{pref}_{q_id}"] = 0
            
        st.markdown("**Opciones de respuesta:**")
        
        for idx_op, op in enumerate(st.session_state[f"opciones{pref}_{q_id}"]):
            c_op1, c_op2 = st.columns([0.85, 0.15])
            with c_op1:
                st.markdown(f"🔹 {op}")
            with c_op2:
                if st.button("✖", key=f"del_op{pref}_{q_id}_{idx_op}"):
                    st.session_state[f"opciones{pref}_{q_id}"].pop(idx_op)
                    st.rerun()
                    
        c_add1, c_add2 = st.columns([0.85, 0.15])
        with c_add1:
            c_key = f"nueva_op{pref}_{q_id}_{st.session_state[f'op_counter{pref}_{q_id}']}"
            nueva_op = st.text_input("Añadir", placeholder="Nueva opción...", label_visibility="collapsed", key=c_key)
        with c_add2:
            if st.button("➕", key=f"btn_add{pref}_{q_id}", use_container_width=True):
                if nueva_op.strip() and nueva_op.strip() not in st.session_state[f"opciones{pref}_{q_id}"]:
                    st.session_state[f"opciones{pref}_{q_id}"].append(nueva_op.strip())
                    st.session_state[f"op_counter{pref}_{q_id}"] += 1
                    st.rerun()
        
        opciones = st.session_state[f"opciones{pref}_{q_id}"]

    # ⚡ Nota Informativa para el usuario en el editor
    if tipo == "Escala Likert (Caritas)":
        st.info("✨ Esta pregunta mostrará las 5 caritas personalizadas (del 1 al 5) en la encuesta.")
        # No necesita 'opciones' manuales porque las caritas son fijas
        opciones = ["1", "2", "3", "4", "5"]
        
    return texto, tipo, opciones
        
    tipos_disp = ["Texto libre", "Opción única", "Opción múltiple", "Escala Likert", "NPS"]
    tipo = st.selectbox("Formato de respuesta:", tipos_disp, key=k_tipo)
    
    opciones = []
    if tipo in ["Opción única", "Opción múltiple"]:
        if f"opciones{pref}_{q_id}" not in st.session_state:
            st.session_state[f"opciones{pref}_{q_id}"] = default_opciones.copy()
        if f"op_counter{pref}_{q_id}" not in st.session_state:
            st.session_state[f"op_counter{pref}_{q_id}"] = 0
            
        st.markdown("**Opciones de respuesta:**")
        
        for idx_op, op in enumerate(st.session_state[f"opciones{pref}_{q_id}"]):
            c_op1, c_op2 = st.columns([0.85, 0.15])
            with c_op1:
                st.markdown(f"🔹 {op}")
            with c_op2:
                if st.button("✖", key=f"del_op{pref}_{q_id}_{idx_op}"):
                    st.session_state[f"opciones{pref}_{q_id}"].pop(idx_op)
                    st.rerun()
                    
        c_add1, c_add2 = st.columns([0.85, 0.15])
        with c_add1:
            c_key = f"nueva_op{pref}_{q_id}_{st.session_state[f'op_counter{pref}_{q_id}']}"
            nueva_op = st.text_input("Añadir", placeholder="Nueva opción...", label_visibility="collapsed", key=c_key)
        with c_add2:
            if st.button("➕", key=f"btn_add{pref}_{q_id}", use_container_width=True):
                if nueva_op.strip() and nueva_op.strip() not in st.session_state[f"opciones{pref}_{q_id}"]:
                    st.session_state[f"opciones{pref}_{q_id}"].append(nueva_op.strip())
                    st.session_state[f"op_counter{pref}_{q_id}"] += 1
                    st.rerun()
        
        opciones = st.session_state[f"opciones{pref}_{q_id}"]
        
    return texto, tipo, opciones
