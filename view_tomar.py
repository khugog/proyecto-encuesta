import streamlit as st
import json
import base64
from bigquery_operations import obtener_encuesta, guardar_respuestas, validar_acceso_encuesta, obtener_lideres_evaluados


def get_base64_image(image_path):
    """Convierte la imagen a base64 para mostrarla en HTML."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""  # Retorna vacío si no encuentra la imagen


def render_tomar_encuesta(encuesta_id):
    cache_key = f"encuesta_data_{encuesta_id}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = obtener_encuesta(encuesta_id)

    encuesta, preguntas = st.session_state[cache_key]

    if not encuesta:
        st.error(
            "⚠️ Esta encuesta no existe, ha sido eliminada o el enlace es incorrecto.")
        return

    if not encuesta.get("activa", True):
        st.error("⚠️ Se ha cerrado la encuesta")
        st.info(
            "Ya no se aceptan más respuestas para este formulario. Gracias por tu interés.")
        return

    logo = encuesta.get("logo_empresa")
    posicion = encuesta.get("logo_position", "Centro")
    color_fondo = encuesta.get("color_fondo", "#FFFFFF")

    # Lógica de color de texto automática según fondo
    if color_fondo:
        try:
            h = color_fondo.lstrip('#')
            r, g, b = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b)
            color_texto = "#111827" if luminance > 160 else "#FFFFFF"
        except BaseException:
            color_texto = "#111827"

        st.markdown(f"""
        <style>
        .stApp {{ background-color: {color_fondo} !important; }}
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp label, .stText {{ color: {color_texto} !important; }}
        .stApp [data-testid="stMarkdownContainer"] p, .stApp [data-testid="stMarkdownContainer"] span {{ color: {color_texto} !important; }}
        [data-testid="stButton"] button[kind="secondary"],
        [data-testid="stFormSubmitButton"] button {{
            background-color: #ffffff !important;
            border: 2px solid #d1d5db !important;
            color: #111827 !important;
        }}
        [data-testid="stButton"] button[kind="secondary"] p,
        [data-testid="stFormSubmitButton"] button p {{
            color: #111827 !important;
        }}
        [data-testid="stButton"] button[kind="primary"] {{
            background-color: #ff4b4b !important;
            border: none !important;
            color: #ffffff !important;
        }}
        [data-testid="stButton"] button[kind="primary"] p {{
            color: #ffffff !important;
        }}

        /* Estilos para caritas */
        .carita-container {{
            display: flex;
            justify-content: space-around;
            padding: 10px 0;
        }}
        .carita-item {{ text-align: center; }}
        .carita-img {{
            width: 60px !important;
            filter: grayscale(100%) !important;
            opacity: 0.4 !important;
            transition: all 0.3s ease !important;
            margin-bottom: 5px;
        }}
        .carita-img.active {{
            filter: grayscale(0%) !important;
            opacity: 1 !important;
            transform: scale(1.2) !important;
        }}
        .carita-label {{
            display: block;
            font-weight: bold;
            margin-top: 5px;
            color: {color_texto} !important;
        }}

        /* ELIMINAR EL BOTON VISUALMENTE Y SUPERPONERLO - SOLO PARA CARITAS */
        div[data-testid="stColumn"]:has(.carita-item) > div > div:nth-child(2) {{
            margin-top: -95px !important;
            z-index: 10 !important;
            position: relative !important;
        }}
        div[data-testid="stColumn"]:has(.carita-item) div[data-testid="stButton"] button {{
            background-color: transparent !important;
            border: none !important;
            color: transparent !important;
            box-shadow: none !important;
            height: 95px !important;
            cursor: pointer !important;
        }}
        div[data-testid="stColumn"]:has(.carita-item) div[data-testid="stButton"] button p {{
            color: transparent !important;
        }}
        div[data-testid="stColumn"]:has(.carita-item) div[data-testid="stButton"] button:hover,
        div[data-testid="stColumn"]:has(.carita-item) div[data-testid="stButton"] button:active,
        div[data-testid="stColumn"]:has(.carita-item) div[data-testid="stButton"] button:focus {{
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: transparent !important;
        }}

        /* Estilos para botones NPS y Likert */
        .nps-item {{ text-align: center; }}
        .nps-btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 45px;
            background-color: transparent;
            border: 2px solid #d1d5db;
            border-radius: 8px;
            font-weight: bold;
            font-size: 1.1rem;
            color: {color_texto} !important;
            transition: all 0.2s ease;
        }}
        .nps-btn.active {{
            background-color: #ff4b4b !important;
            border-color: #ff4b4b !important;
            color: #ffffff !important;
            transform: scale(1.05);
        }}

        /* ELIMINAR EL BOTON VISUALMENTE Y SUPERPONERLO - PARA NPS/LIKERT */
        div[data-testid="stColumn"]:has(.nps-item) > div > div:nth-child(2) {{
            margin-top: -60px !important;
            z-index: 10 !important;
            position: relative !important;
        }}
        div[data-testid="stColumn"]:has(.nps-item) div[data-testid="stButton"] button {{
            background-color: transparent !important;
            border: none !important;
            color: transparent !important;
            box-shadow: none !important;
            height: 60px !important;
            cursor: pointer !important;
        }}
        div[data-testid="stColumn"]:has(.nps-item) div[data-testid="stButton"] button p {{
            color: transparent !important;
        }}
        div[data-testid="stColumn"]:has(.nps-item) div[data-testid="stButton"] button:hover,
        div[data-testid="stColumn"]:has(.nps-item) div[data-testid="stButton"] button:active,
        div[data-testid="stColumn"]:has(.nps-item) div[data-testid="stButton"] button:focus {{
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: transparent !important;
        }}
        </style>
        """, unsafe_allow_html=True)

    # Renderizado de Logo
    align = "left" if posicion == "Izquierda" else "right" if posicion == "Derecha" else "center"
    if logo:
        st.markdown(
            f"<div style='text-align: {align}; margin-top: 15px; margin-bottom: 15px;'><img src='data:image/png;base64,{logo}' style='max-width: 200px; max-height: 100px; border-radius: 8px; object-fit: contain;'></div>",
            unsafe_allow_html=True)

    st.title(encuesta.get("titulo", "Encuesta"))
    if encuesta.get("descripcion"):
        st.markdown(
            f"<p style='color: {color_texto}; opacity: 0.8; font-size: 1.1rem; text-align: center;'>{
                encuesta.get('descripcion')}</p>",
            unsafe_allow_html=True)

    st.divider()

    # --- VALIDACIÓN DE ACCESO (EL AVANCE QUE SE PERDIÓ) ---
    auth_key = f"auth_{encuesta_id}"
    demographics = None
    tipo_acceso = encuesta.get("tipo_acceso") or ""
    if "Privada" in tipo_acceso:
        if auth_key not in st.session_state:
            st.session_state[auth_key] = False
        if not st.session_state[auth_key]:
            st.warning(
                "🔒 Esta encuesta es privada. Identifícate para continuar.")
            with st.form("login_dni"):
                st.info(
                    "Ingresa tu Dato Validador para acceder al formulario personalizado.")
                dni_input = st.text_input(
                    "Dato Validador (DNI / Cédula)",
                    placeholder="Escribe tu número de identificación")
                if st.form_submit_button("Validar e Ingresar"):
                    datos_lista = validar_acceso_encuesta(
                        encuesta_id, dni_input.strip())
                    if datos_lista:
                        st.session_state[auth_key] = True
                        st.session_state[f"demo_list_{encuesta_id}"] = datos_lista
                        # Clear any existing evaluated cache just in case
                        if f"evaluados_{encuesta_id}" in st.session_state:
                            del st.session_state[f"evaluados_{encuesta_id}"]
                        st.success("✅ Acceso concedido.")
                        st.rerun()
                    else:
                        st.error(
                            "❌ El dato ingresado no se encuentra en el padrón de esta encuesta.")
            return

        demographics_list = st.session_state.get(f"demo_list_{encuesta_id}")

        evaluados_key = f"evaluados_{encuesta_id}"
        if evaluados_key not in st.session_state:
            st.session_state[evaluados_key] = obtener_lideres_evaluados(
                encuesta_id, demographics_list[0].get('dni', ''))

        evaluados = st.session_state[evaluados_key]

        lideres_disponibles = [d for d in demographics_list if d.get(
            'lider_directo') not in evaluados]

        if not lideres_disponibles:
            st.success(
                "✅ Has completado todas las evaluaciones asignadas para esta encuesta. ¡Muchas gracias por tu tiempo!")
            if st.button("Volver al inicio", use_container_width=True):
                st.session_state[auth_key] = False
                if f"demo_list_{encuesta_id}" in st.session_state:
                    del st.session_state[f"demo_list_{encuesta_id}"]
                if evaluados_key in st.session_state:
                    del st.session_state[evaluados_key]
                st.rerun()
            return

        seleccion_key = f"lider_seleccionado_{encuesta_id}"
        if seleccion_key not in st.session_state:
            st.info(
                f"👋 Hola {
                    demographics_list[0].get(
                        'nombre_completo',
                        'Usuario')}, tienes evaluaciones pendientes.")
            opciones = ["Seleccione una opción"] + \
                [d.get('lider_directo') for d in lideres_disponibles]
            seleccion = st.selectbox("A quién deseas evaluar?", opciones)
            if seleccion != "Seleccione una opción":
                if st.button("Empezar", use_container_width=True):
                    st.session_state[seleccion_key] = next(
                        d for d in lideres_disponibles if d.get('lider_directo') == seleccion)
                    st.rerun()
            st.write("")
            if st.button("Cerrar Sesión", use_container_width=True):
                st.session_state[auth_key] = False
                if f"demo_list_{encuesta_id}" in st.session_state:
                    del st.session_state[f"demo_list_{encuesta_id}"]
                if evaluados_key in st.session_state:
                    del st.session_state[evaluados_key]
                st.rerun()
            return

        demographics = st.session_state[seleccion_key]

    if st.session_state.get(f"completado_{encuesta_id}", False):
        st.success("✅ ¡Muchas gracias por participar!")
        if "Privada" in tipo_acceso:
            demographics_list = st.session_state.get(f"demo_list_{encuesta_id}", [])
            evaluados = st.session_state.get(f"evaluados_{encuesta_id}", [])
            lideres_pendientes = [d for d in demographics_list if d.get('lider_directo') not in evaluados]
            
            if lideres_pendientes:
                if st.button("Evaluar siguiente líder", use_container_width=True):
                    st.session_state[f"completado_{encuesta_id}"] = False
                    if f"lider_seleccionado_{encuesta_id}" in st.session_state:
                        del st.session_state[f"lider_seleccionado_{encuesta_id}"]
                    st.rerun()
            else:
                if st.button("Volver al inicio", use_container_width=True):
                    st.session_state[f"completado_{encuesta_id}"] = False
                    st.session_state[auth_key] = False
                    if f"demo_list_{encuesta_id}" in st.session_state:
                        del st.session_state[f"demo_list_{encuesta_id}"]
                    if f"evaluados_{encuesta_id}" in st.session_state:
                        del st.session_state[f"evaluados_{encuesta_id}"]
                    if f"lider_seleccionado_{encuesta_id}" in st.session_state:
                        del st.session_state[f"lider_seleccionado_{encuesta_id}"]
                    st.rerun()
        return

    if demographics:
        st.info(f"📝 Evaluando a: **{demographics.get('lider_directo')}**")

    # --- RENDERIZADO DE PREGUNTAS ---
    respuestas = {}
    for idx, p in enumerate(preguntas):
        pid = p["id"]
        st.markdown(f"**{idx + 1}. {p['texto_pregunta']}**")
        tipo = p["tipo_pregunta"]
        ops = json.loads(p.get("opciones") or "[]")

        if tipo == "Texto libre":
            respuestas[pid] = st.text_input(
                "Tu respuesta",
                key=f"resp_{pid}",
                label_visibility="collapsed")

        elif tipo == "Escala Likert (Caritas)":
            # Nombres de tus archivos
            caritas_files = [
                "cara-bad-step1.png", "cara-triste-step2.png", "cara-medio-step3.png",
                "cara-feli-step4.png", "cara-superfeliz-step5.png"
            ]

            # Recuperar selección previa del session_state
            key_likert = f"resp_{pid}"
            if key_likert not in st.session_state:
                st.session_state[key_likert] = None

            # Crear las columnas para las 5 caritas
            cols = st.columns(5)
            for i, col in enumerate(cols):
                val = str(i + 1)
                is_active = "active" if st.session_state[key_likert] == val else ""
                img_b64 = get_base64_image(caritas_files[i])

                with col:
                    # Mostrar la imagen con el efecto de color
                    st.markdown(f"""
                        <div class="carita-item">
                            <img src="data:image/png;base64,{img_b64}" class="carita-img {is_active}">
                            <span class="carita-label">{val}</span>
                        </div>
                    """, unsafe_allow_html=True)

                    # Botón para seleccionar (Ahora es invisible gracias al
                    # CSS)
                    if st.button(
                            " ", key=f"btn_{pid}_{val}", use_container_width=True):
                        st.session_state[key_likert] = val
                        st.rerun()

            # Guardar con formato de texto extendido
            likert_labels = {
                "1": "1.- Muy triste",
                "2": "2.- Triste",
                "3": "3.- Neutral",
                "4": "4.- Feliz",
                "5": "5.- Muy Feliz"
            }
            val_seleccionado = st.session_state[key_likert]
            respuestas[pid] = likert_labels.get(
                val_seleccionado, val_seleccionado)
        elif tipo == "Escala Likert":
            key_likert = f"resp_{pid}"
            if key_likert not in st.session_state:
                st.session_state[key_likert] = None
            cols = st.columns(5)
            for i, col in enumerate(cols):
                val = str(i + 1)
                is_active = "active" if st.session_state[key_likert] == val else ""
                with col:
                    st.markdown(
                        f'<div class="nps-item"><div class="nps-btn {is_active}">{val}</div></div>',
                        unsafe_allow_html=True)
                    if st.button(
                            " ", key=f"btn_{pid}_{val}", use_container_width=True):
                        st.session_state[key_likert] = val
                        st.rerun()
            respuestas[pid] = st.session_state[key_likert]

        elif tipo == "NPS":
            key_nps = f"resp_{pid}"
            if key_nps not in st.session_state:
                st.session_state[key_nps] = None
            cols = st.columns(10)
            for i, col in enumerate(cols):
                val = str(i + 1)
                is_active = "active" if st.session_state[key_nps] == val else ""
                with col:
                    st.markdown(
                        f'<div class="nps-item"><div class="nps-btn {is_active}">{val}</div></div>',
                        unsafe_allow_html=True)
                    if st.button(
                            " ", key=f"btn_{pid}_{val}", use_container_width=True):
                        st.session_state[key_nps] = val
                        st.rerun()
            respuestas[pid] = st.session_state[key_nps]

        elif tipo == "Opción única":
            respuestas[pid] = st.radio(
                "Selecciona",
                ops,
                key=f"resp_{pid}",
                index=None,
                label_visibility="collapsed")
        elif tipo == "Opción múltiple":
            seleccionadas = []
            for op in ops:
                if st.checkbox(op, key=f"resp_{pid}_{op}"):
                    seleccionadas.append(op)
            respuestas[pid] = seleccionadas
        st.write("")

    st.divider()
    if st.button("Enviar Mis Respuestas", type="primary",
                 use_container_width=True):
        guardar_respuestas(encuesta_id, respuestas, demographics=demographics)
        st.session_state[f"completado_{encuesta_id}"] = True
        
        if "Privada" in tipo_acceso and demographics:
            eval_key = f"evaluados_{encuesta_id}"
            if eval_key in st.session_state:
                st.session_state[eval_key].append(demographics.get('lider_directo'))
                
        st.rerun()
