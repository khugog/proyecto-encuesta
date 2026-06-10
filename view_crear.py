import streamlit as st
import uuid
import base64
import pandas as pd
from bigquery_operations import crear_encuesta
from components import render_question_builder_fields


def get_base64_image(image_path):
    """Convierte la imagen a base64 para mostrarla en HTML."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""  # Retorna vacío si no encuentra la imagen

# --- CALLBACKS Y LOGICA DE ESTADO ---


def callback_crear_encuesta():
    st.session_state["creando_encuesta_db"] = True


def callback_seguir_editando():
    c = st.session_state.backup_crear
    st.session_state["crear_titulo"] = c.get("titulo", "")
    st.session_state["crear_desc"] = c.get("descripcion", "")
    st.session_state["crear_emp"] = c.get("empresa_dirigida", "")
    st.session_state["crear_align"] = c.get("logo_position", "Centro")
    st.session_state["crear_color"] = c.get("color_fondo", "#FFFFFF")
    st.session_state["crear_acc"] = c.get("tipo_acceso", "Pública")

    preg_ids = []
    for p in c.get("preguntas", []):
        q_id = p["id"]
        preg_ids.append(q_id)
        st.session_state[f"texto_{q_id}"] = p["texto"]
        st.session_state[f"tipo_{q_id}"] = p["tipo"]
        st.session_state[f"opciones_{q_id}"] = p["opciones"]
        st.session_state[f"op_counter_{q_id}"] = len(p["opciones"])

    st.session_state["preguntas_ids"] = preg_ids
    st.session_state["global_df_padron_temp"] = c.get("df_padron")
    st.session_state["global_df_padron_variables_temp"] = c.get("df_padron_variables")
    st.session_state["fase_vista"] = "formulario"
    st.toast("✏️ Regresando al modo edición...")


def callback_previsualizar_encuesta():
    titulo = st.session_state.get("crear_titulo", "")
    descripcion = st.session_state.get("crear_desc", "")
    empresa_dirigida = st.session_state.get("crear_emp", "")
    logo_position = st.session_state.get("crear_align", "Centro")
    color_fondo = st.session_state.get("crear_color", "#FFFFFF")
    tipo_acceso = st.session_state.get("crear_acc", "Pública")

    preguntas_reales = []
    for q_id in st.session_state.get("preguntas_ids", []):
        texto_real = st.session_state.get(f"texto_{q_id}", "").strip()
        tipo_real = st.session_state.get(f"tipo_{q_id}", "Texto libre")
        ops_reales = st.session_state.get(f"opciones_{q_id}", [])
        preguntas_reales.append({
            "id": q_id, "texto": texto_real, "tipo": tipo_real, "opciones": ops_reales
        })

    # Validación antes de preview
    hay_error = False
    errores = []
    if not titulo.strip():
        errores.append("⚠️ El título es obligatorio.")
        hay_error = True
    if len(preguntas_reales) == 0:
        errores.append("⚠️ Debes agregar al menos una pregunta.")
        hay_error = True

    if hay_error:
        st.session_state["preview_errores"] = errores
    else:
        if "preview_errores" in st.session_state:
            del st.session_state["preview_errores"]
        enc_b64 = st.session_state.get("global_logo_base64_temp", "")
        from padron_variables import mapping_to_json
        st.session_state.backup_crear = {
            "titulo": titulo, "descripcion": descripcion, "empresa_dirigida": empresa_dirigida,
            "logo_position": logo_position, "color_fondo": color_fondo, "tipo_acceso": tipo_acceso,
            "df_padron": st.session_state.get("global_df_padron_temp"),
            "variables_padron": mapping_to_json(
                st.session_state.get("padron_variable_mapping", [])
            ),
            "df_padron_variables": st.session_state.get("global_df_padron_variables_temp"),
            "variables_padron_analysis": mapping_to_json(
                st.session_state.get("padron_variables_variable_mapping", [])
            ),
            "logo_empresa_b64": enc_b64, "preguntas": preguntas_reales
        }
        st.session_state["fase_vista"] = "preview"


def render_escenario_preview():
    st.markdown(
        "<h2 style='text-align: center;'>👁️ Previsualización del Formulario</h2>",
        unsafe_allow_html=True)
    backup = st.session_state.backup_crear
    color_fondo = backup.get("color_fondo", "#FFFFFF")

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

    </style>

    <style>
    /* Estilos para caritas en Preview */
    .carita-container {{
        display: flex;
        justify-content: space-around;
        padding: 10px 0;
    }}
    .carita-item {{ text-align: center; }}
    .carita-img {{
        width: 50px !important;
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
        margin-top: -85px !important;
        z-index: 10 !important;
        position: relative !important;
    }}
    div[data-testid="stColumn"]:has(.carita-item) div[data-testid="stButton"] button {{
        background-color: transparent !important;
        border: none !important;
        color: transparent !important;
        box-shadow: none !important;
        height: 85px !important;
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

    /* Estilos para botones generales (los de abajo) */
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

    [data-testid="stButton"] button[kind="primary"],
    [data-testid="stFormSubmitButton"] button[kind="primary"] {{
        background-color: #ff4b4b !important;
        border: none !important;
        color: #ffffff !important;
    }}
    [data-testid="stButton"] button[kind="primary"] p,
    [data-testid="stFormSubmitButton"] button[kind="primary"] p {{
        color: #ffffff !important;
    }}

    /* ELIMINAR EL BOTON VISUALMENTE Y SUPERPONERLO - SOLO PARA CARITAS */
    div[data-testid="stColumn"]:has(.carita-item) > div > div:nth-child(2) {{
        margin-top: -85px !important;
        z-index: 10 !important;
        position: relative !important;
    }}
    div[data-testid="stColumn"]:has(.carita-item) div[data-testid="stButton"] button {{
        background-color: transparent !important;
        border: none !important;
        color: transparent !important;
        box-shadow: none !important;
        height: 85px !important;
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
    </style>
    """, unsafe_allow_html=True)

    if backup.get("logo_empresa_b64"):
        align = "left" if backup.get("logo_position") == "Izquierda" else "right" if backup.get(
            "logo_position") == "Derecha" else "center"
        st.markdown(
            f"<div style='text-align: {align}; margin-bottom: 15px;'><img src='data:image/png;base64,{
                backup.get('logo_empresa_b64')}' style='max-width: 200px; max-height: 100px; object-fit: contain;'></div>",
            unsafe_allow_html=True)

    st.title(backup.get("titulo", ""))
    if backup.get("descripcion"):
        st.markdown(
            f"<p style='text-align:center; opacity:0.8;'>{
                backup.get('descripcion')}</p>",
            unsafe_allow_html=True)
    st.divider()

    for idx, p in enumerate(backup.get("preguntas", [])):
        st.markdown(f"**{idx + 1}. {p['texto']}**")

        if p['tipo'] == "Texto libre":
            st.text_input(
                "Tu respuesta",
                key=f"prev_{idx}",
                label_visibility="collapsed")

        elif p['tipo'] == "Escala Likert (Caritas)":
            caritas_files = [
                "cara-bad-step1.png", "cara-triste-step2.png", "cara-medio-step3.png",
                "cara-feli-step4.png", "cara-superfeliz-step5.png"
            ]
            key_likert_prev = f"prev_likert_{idx}"
            if key_likert_prev not in st.session_state:
                st.session_state[key_likert_prev] = None

            cols = st.columns(5)
            for i, col in enumerate(cols):
                val = str(i + 1)
                is_active = "active" if st.session_state[key_likert_prev] == val else ""
                img_b64 = get_base64_image(caritas_files[i])
                with col:
                    st.markdown(f"""
                        <div class="carita-item">
                            <img src="data:image/png;base64,{img_b64}" class="carita-img {is_active}">
                            <span class="carita-label">{val}</span>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(
                            " ", key=f"prev_btn_{idx}_{i}", use_container_width=True):
                        st.session_state[key_likert_prev] = val
                        st.rerun()

        elif p['tipo'] == "Escala Likert":
            key_likert_prev = f"prev_likert_num_{idx}"
            if key_likert_prev not in st.session_state:
                st.session_state[key_likert_prev] = None
            cols = st.columns(5)
            for i, col in enumerate(cols):
                val = str(i + 1)
                is_active = "active" if st.session_state[key_likert_prev] == val else ""
                with col:
                    st.markdown(
                        f'<div class="nps-item"><div class="nps-btn {is_active}">{val}</div></div>',
                        unsafe_allow_html=True)
                    if st.button(
                            " ", key=f"prev_btn_likert_{idx}_{val}", use_container_width=True):
                        st.session_state[key_likert_prev] = val
                        st.rerun()

        elif p['tipo'] == "NPS":
            key_nps_prev = f"prev_nps_{idx}"
            if key_nps_prev not in st.session_state:
                st.session_state[key_nps_prev] = None
            cols = st.columns(10)
            for i, col in enumerate(cols):
                val = str(i + 1)
                is_active = "active" if st.session_state[key_nps_prev] == val else ""
                with col:
                    st.markdown(
                        f'<div class="nps-item"><div class="nps-btn {is_active}">{val}</div></div>',
                        unsafe_allow_html=True)
                    if st.button(
                            " ", key=f"prev_btn_nps_{idx}_{val}", use_container_width=True):
                        st.session_state[key_nps_prev] = val
                        st.rerun()

        elif p['tipo'] == "Opción múltiple":
            ops = p['opciones'] if p['opciones'] else ["Sin opciones"]
            for op in ops:
                st.checkbox(op, key=f"prev_{idx}_{op}")

        elif p['tipo'] == "Opción única":
            st.radio(
                "Seleccione",
                p['opciones'] if p['opciones'] else ["Sin opciones"],
                key=f"prev_{idx}",
                index=None,
                label_visibility="collapsed")

        else:
            st.radio(
                "Seleccione",
                p['opciones'] if p['opciones'] else ["Sin opciones"],
                key=f"prev_{idx}",
                label_visibility="collapsed")
        st.write("")

    c_btn1, c_btn2 = st.columns(2)
    bloqueado = st.session_state.get("creando_encuesta_db", False)
    with c_btn1:
        st.button(
            "⬅️ Seguir Editando Formulario",
            use_container_width=True,
            disabled=bloqueado,
            on_click=callback_seguir_editando)
    with c_btn2:
        if st.button("🚀 Confirmar y Finalizar Encuesta", type="primary",
                     use_container_width=True, disabled=bloqueado):
            callback_crear_encuesta()
            st.rerun()

        if bloqueado:
            enc_id = crear_encuesta(
                titulo=backup.get("titulo"), descripcion=backup.get("descripcion"), preguntas=backup.get("preguntas"),
                tipo_acceso=backup.get("tipo_acceso"), df_padron=backup.get("df_padron"), empresa_dirigida=backup.get("empresa_dirigida"),
                logo_empresa=backup.get("logo_empresa_b64"), logo_position=backup.get("logo_position"), color_fondo=backup.get("color_fondo"),
                variables_padron=backup.get("variables_padron", ""),
            )
            st.session_state["encuesta_creada_id"] = enc_id
            st.session_state["fase_vista"] = "formulario"
            st.rerun()


def render_escenario_form():
    st.title("🎯 Constructor de Encuestas")

    st.markdown("### 📝 Información General")
    st.text_input(
        "Título de la Encuesta",
        placeholder="Ej. Encuesta de Satisfacción 2024",
        key="crear_titulo")
    st.text_area(
        "Descripción (Opcional)",
        placeholder="Escribe el propósito de esta encuesta...",
        key="crear_desc")

    st.markdown("### 🎨 Personalización y Logo")
    st.selectbox(
        "Empresa Destino", [
            "", "Plaza Vea", "Oslo", "Mass", "Makro", "EPA"], key="crear_emp")

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.selectbox(
            "Alineación del Logo", [
                "Izquierda", "Centro", "Derecha"], key="crear_align")
    with col_v2:
        logo = st.file_uploader(
            "Subir Logo Corporativo", type=[
                "png", "jpg", "jpeg"])

    if "crear_color" not in st.session_state:
        st.session_state["crear_color"] = "#FFFFFF"
    st.color_picker("Color de Fondo", key="crear_color")

    if logo:
        logo_b64 = base64.b64encode(logo.getvalue()).decode("utf-8")
        st.session_state["global_logo_base64_temp"] = logo_b64
        st.image(logo.getvalue(), caption="Vista previa del logo", width=150)
    elif st.session_state.get("global_logo_base64_temp"):
        st.image(
            base64.b64decode(
                st.session_state["global_logo_base64_temp"]),
            caption="Logo cargado",
            width=150)

    st.markdown("### 🔒 Control de Acceso")
    acceso = st.radio(
        "Tipo de Acceso", [
            "Pública", "Privada (Requiere Padrón)"], horizontal=True, key="crear_acc")
    if "Privada" in acceso:
        col_up, col_dl = st.columns([0.7, 0.3])

        from padron_variables import (
            apply_padron_mapping,
            generate_padron_template_bytes,
            generate_padron_lider_template_bytes,
            render_padron_variable_mapper,
        )

        with col_dl:
            st.markdown(
                "<p class='brand-link' style='font-size: 18px; margin-bottom: 6px; margin-top: 2px;'>"
                "✨ Plantilla Padrón</p>",
                unsafe_allow_html=True,
            )
            st.download_button(
                label="⬇️ Descargar Plantilla",
                data=generate_padron_lider_template_bytes(),
                file_name="Plantilla_Padron.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.caption(
                "Columnas **DNI**, **Nombre Completo** y **Líder Directo** obligatorias."
            )

        with col_up:
            st.markdown(
                "<p style='font-size: 18px; margin-bottom: 10px;'>📂 Adjuntar Archivo de Padrón</p>",
                unsafe_allow_html=True,
            )
            padron = st.file_uploader(
                "", type=["xlsx", "xls"], label_visibility="collapsed", key="crear_padron")
            if padron:
                from padron_variables import build_default_mapping, apply_padron_mapping
                df_raw = pd.read_excel(padron)
                mapping = build_default_mapping(df_raw.columns)
                st.session_state["global_df_padron_temp"] = apply_padron_mapping(
                    df_raw, mapping
                )
                st.success("✅ Padrón cargado exitosamente.")

        st.divider()

        col_up2, col_dl2 = st.columns([0.7, 0.3])

        with col_dl2:
            st.markdown(
                "<p class='brand-link' style='font-size: 18px; margin-bottom: 6px; margin-top: 2px;'>"
                "✨ Plantilla variables</p>",
                unsafe_allow_html=True,
            )
            st.download_button(
                label="⬇️ Descargar Plantilla",
                data=generate_padron_template_bytes(),
                file_name="Plantilla_Padron_Variables.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.caption(
                "Columna **DNI** obligatoria. Las variables adicionales se detectan "
                "automáticamente del Excel. Puedes agregar más columnas según necesites."
            )

        with col_up2:
            st.markdown(
                "<p style='font-size: 18px; margin-bottom: 10px;'>📂 Adjuntar Variables de Análisis (Opcional)</p>",
                unsafe_allow_html=True,
            )
            padron_variables = st.file_uploader(
                "", type=["xlsx", "xls"], label_visibility="collapsed", key="crear_padron_variables")
            if padron_variables:
                df_raw = pd.read_excel(padron_variables)
                mapping = render_padron_variable_mapper(df_raw)
                st.session_state["global_df_padron_variables_temp"] = apply_padron_mapping(
                    df_raw, mapping
                )
                st.success("✅ Variables de análisis cargadas y configuradas.")

    st.markdown("### ❓ Preguntas")
    if "preguntas_ids" not in st.session_state:
        st.session_state.preguntas_ids = [str(uuid.uuid4())]
    for idx, q_id in enumerate(st.session_state.preguntas_ids):
        with st.container(border=True):
            st.markdown(f"**Pregunta {idx + 1}**")
            col1, col2 = st.columns([0.9, 0.1])
            with col2:
                if st.button("🗑️", key=f"del_{q_id}"):
                    st.session_state.preguntas_ids.remove(q_id)
                    st.rerun()
            with col1:
                render_question_builder_fields(q_id)

    if st.button("➕ Añadir Pregunta"):
        st.session_state.preguntas_ids.append(str(uuid.uuid4()))
        st.rerun()

    if "preview_errores" in st.session_state:
        for err in st.session_state["preview_errores"]:
            st.error(err)

    st.button(
        "👁️ Previsualizar Encuesta",
        type="primary",
        use_container_width=True,
        on_click=callback_previsualizar_encuesta)


def render_crear_encuesta():
    st.markdown("""
    <style>
    /* CSS GLOBAL PARA EVITAR PARPADEO DE BOTONES FANTASMA EN TRANSICIONES */
    div[data-testid="stColumn"]:has(.carita-item) > div > div:nth-child(2) { margin-top: -85px !important; z-index: 10 !important; position: relative !important; }
    div[data-testid="stColumn"]:has(.nps-item) > div > div:nth-child(2) { margin-top: -60px !important; z-index: 10 !important; position: relative !important; }

    div[data-testid="stColumn"]:has(.carita-item) div[data-testid="stButton"] button,
    div[data-testid="stColumn"]:has(.nps-item) div[data-testid="stButton"] button,
    div[data-testid="stColumn"]:has(.carita-item) div[data-testid="stButton"] button:hover,
    div[data-testid="stColumn"]:has(.carita-item) div[data-testid="stButton"] button:active,
    div[data-testid="stColumn"]:has(.carita-item) div[data-testid="stButton"] button:focus,
    div[data-testid="stColumn"]:has(.nps-item) div[data-testid="stButton"] button:hover,
    div[data-testid="stColumn"]:has(.nps-item) div[data-testid="stButton"] button:active,
    div[data-testid="stColumn"]:has(.nps-item) div[data-testid="stButton"] button:focus {
        background-color: transparent !important;
        border: none !important;
        color: transparent !important;
        box-shadow: none !important;
        cursor: pointer !important;
    }
    div[data-testid="stColumn"]:has(.carita-item) div[data-testid="stButton"] button p,
    div[data-testid="stColumn"]:has(.nps-item) div[data-testid="stButton"] button p {
        color: transparent !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if "backup_crear" not in st.session_state:
        st.session_state.backup_crear = {}
    fase = st.session_state.get("fase_vista", "formulario")

    if "encuesta_creada_id" in st.session_state:
        enc_id = st.session_state["encuesta_creada_id"]
        st.success(f"✅ ¡Encuesta creada con éxito! ID: {enc_id}")
        if st.button("Crear otra encuesta"):
            del st.session_state["encuesta_creada_id"]
            st.rerun()
    elif fase == "preview":
        render_escenario_preview()
    else:
        render_escenario_form()
