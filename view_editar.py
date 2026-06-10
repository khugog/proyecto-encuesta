import streamlit as st
import json
import uuid
import base64
from bigquery_operations import obtener_encuesta, editar_metadata_encuesta, editar_pregunta, eliminar_pregunta, agregar_nuevas_preguntas, obtener_padron, agregar_padron, eliminar_colaboradores_masivo, modificar_lideres_masivo
from components import render_question_builder_fields


def render_editar_encuesta(encuesta_id):
    st.button(
        "⬅️ Volver a Mis Encuestas",
        on_click=lambda: st.session_state.pop(
            "editando_encuesta_id",
            None))

    enc, preguntas_existentes = obtener_encuesta(encuesta_id)

    if not enc:
        st.error("No se encontró la encuesta.")
        return

    st.title("✏️ Editar Encuesta")
    
    nuevo_excel = None
    excel_baja = None
    excel_mod = None

    with st.container():
        titulo_nuevo = st.text_input(
            "Título", value=enc.get(
                "titulo", ""), max_chars=100)
        desc_nueva = st.text_area(
            "Descripción", value=enc.get(
                "descripcion", ""))

        st.markdown("### 🎨 Apariencia y Detalles")

        opciones_empresa = ["", "Plaza Vea", "Oslo", "Mass",
                            "Makro", "EPA( Empresa Productora de alimentos)"]
        emp_actual = enc.get("empresa_dirigida", "")
        idx_emp = opciones_empresa.index(
            emp_actual) if emp_actual in opciones_empresa else 0

        pos_actual = enc.get("logo_position", "Centro")
        opciones_pos = ["Izquierda", "Centro", "Derecha"]
        idx_pos = opciones_pos.index(
            pos_actual) if pos_actual in opciones_pos else 1

        color_fondo_actual = enc.get("color_fondo", "#FFFFFF")
        if not color_fondo_actual:
            color_fondo_actual = "#FFFFFF"

        # 1. Dirigido a
        empresa_dirigida_nueva = st.selectbox(
            "🎯 Dirigido a:", opciones_empresa, index=idx_emp)

        st.markdown("<br>", unsafe_allow_html=True)

        # 2. Subir Imagen
        c_img1, c_img2 = st.columns([0.7, 0.3])
        with c_img1:
            st.markdown("**🖼️ Subir imagen / logo (Opcional)**")
            nuevo_logo_empresa = st.file_uploader(
                "Adjuntar archivo", type=[
                    "png", "jpg", "jpeg"], label_visibility="collapsed")
            logo_actual = enc.get("logo_empresa", "")

        with c_img2:
            st.markdown("**📍 Alineación de la imagen:**")
            nueva_logo_position = st.selectbox(
                "Alineación",
                opciones_pos,
                index=idx_pos,
                label_visibility="collapsed")

        logo_preview = ""
        if nuevo_logo_empresa:
            logo_preview = base64.b64encode(
                nuevo_logo_empresa.getvalue()).decode("utf-8")
        elif logo_actual:
            logo_preview = logo_actual

        if logo_preview:
            st.markdown("**Previsualización:**")
            align = "left" if nueva_logo_position == "Izquierda" else "right" if nueva_logo_position == "Derecha" else "center"
            st.markdown(
                f"<div style='text-align: {align};'><img src='data:image/png;base64,{logo_preview}' style='max-width: 150px; max-height: 80px; border-radius: 8px; object-fit: contain;'></div>",
                unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 4. Color de fondo
        st.markdown("**🎨 Color de fondo de la encuesta:**")
        nuevo_color_fondo = st.color_picker(
            "🎨 Color de fondo", color_fondo_actual)



        # Mostrar Padrón si es Privada
        if "Privada" in enc.get("tipo_acceso", ""):
            st.divider()
            st.markdown("### 👥 Padrón de Participantes")
            
            col_izq, col_der = st.columns(2, gap="large")
            
            with col_izq:
                with st.container(border=True):
                    st.markdown("**📄 Excel adjuntado**")
                    df_padron = obtener_padron(encuesta_id)
                    if df_padron is not None and not df_padron.empty:
                        st.success(f"✅ Se encontraron {len(df_padron)} registros en el padrón de esta encuesta.")
                        with st.expander("👁️ Ver datos del Excel subido", expanded=False):
                            st.dataframe(df_padron, use_container_width=True, hide_index=True)
                    else:
                        st.warning("⚠️ No se encontró padrón guardado para esta encuesta. Es posible que haya ocurrido un error al crearla o que no se haya adjuntado el archivo.")
            
            with col_der:
                with st.container(border=True):
                    import pandas as pd
                    try:
                        from padron_variables import (
                            apply_padron_mapping,
                            build_default_mapping,
                            generate_padron_template_bytes,
                            generate_padron_lider_template_bytes,
                            mapping_to_json,
                            render_padron_variable_mapper,
                        )
                    except ImportError:
                        st.error("Error al cargar módulo de variables de padrón")
                        return

                    st.markdown("### ➕ Agregar personas al padrón")
                    st.download_button(
                        label="⬇️ Plantilla Padrón",
                        data=generate_padron_lider_template_bytes(),
                        file_name="Plantilla_Padron.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                    st.markdown(
                        "<p style='font-size: 18px; margin-bottom: 10px;'>📂 Subir archivo Excel</p>",
                        unsafe_allow_html=True,
                    )
                    nuevo_excel = st.file_uploader(
                        "",
                        type=["xlsx", "xls"],
                        label_visibility="collapsed",
                        key="edit_nuevo_padron",
                    )
                    if nuevo_excel:
                        df_raw = pd.read_excel(nuevo_excel)
                        mapping = build_default_mapping(df_raw.columns)
                        st.session_state["edit_padron_df_mapped"] = (
                            apply_padron_mapping(df_raw, mapping)
                        )
                        st.session_state["edit_padron_mapping_json"] = (
                            mapping_to_json(mapping)
                        )
                        st.success(
                            "✅ Archivo listo. Pulse **Guardar cambios** para incorporarlo."
                        )

            st.divider()

            with col_der:
                with st.container(border=True):
                    import pandas as pd
                    try:
                        from padron_variables import (
                            apply_padron_mapping,
                            generate_padron_template_bytes,
                            mapping_to_json,
                            render_padron_variable_mapper,
                        )
                    except ImportError:
                        st.error("Error al cargar módulo de variables de padrón")
                        return

                    st.markdown("### ➕ Agregar variables de análisis (Opcional)")
                    st.download_button(
                        label="⬇️ Plantilla variables (DNI + Var.2–5)",
                        data=generate_padron_template_bytes(),
                        file_name="Plantilla_Padron_Variables.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                    st.markdown(
                        "<p style='font-size: 18px; margin-bottom: 10px;'>📂 Subir archivo Excel de variables</p>",
                        unsafe_allow_html=True,
                    )
                    nuevo_excel_variables = st.file_uploader(
                        "",
                        type=["xlsx", "xls"],
                        label_visibility="collapsed",
                        key="edit_nuevo_padron_variables",
                    )
                    if nuevo_excel_variables:
                        df_raw = pd.read_excel(nuevo_excel_variables)
                        mapping = render_padron_variable_mapper(
                            df_raw, state_prefix="edit_variables_"
                        )
                        st.session_state["edit_padron_variables_df_mapped"] = (
                            apply_padron_mapping(df_raw, mapping)
                        )
                        st.session_state["edit_padron_variables_mapping_json"] = (
                            mapping_to_json(mapping)
                        )
                        st.success(
                            "✅ Variables de análisis listas. Pulse **Guardar cambios** para incorporarlas."
                        )

            st.divider()
            st.markdown("### ⚙️ Gestión Masiva de Padrón")
            col_baja, col_mod = st.columns([0.4, 0.6], gap="large")
            with col_baja:
                with st.container(border=True):
                    st.markdown("**🗑️ Baja Masiva de Colaboradores**")
                    st.caption("Sube un Excel con los DNI a eliminar.")
                    excel_baja = st.file_uploader("Subir Excel para Bajas", type=["xlsx", "xls"], key="baja_masiva", label_visibility="collapsed")

            with col_mod:
                with st.container(border=True):
                    st.markdown("**🔄 Modificación Masiva de Líderes**")
                    st.caption("Sube la Plantilla de Modificación con los DNI y los Nuevos Líderes.")
                    
                    c_up, c_dl = st.columns([0.65, 0.35])
                    
                    with c_dl:
                        st.markdown(
                            "<div style='margin-top: 10px;'><p style='font-size: 15px; font-weight: bold; color: #ff4b4b; margin-bottom: 8px;'>✨ Plantilla Excel</p></div>",
                            unsafe_allow_html=True)
                        try:
                            with open("Plantilla_Modificación.xlsx", "rb") as template_file:
                                st.download_button(
                                    label="⬇️ Descargar",
                                    data=template_file,
                                    file_name="Plantilla_Modificación.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                        except Exception:
                            pass

                    with c_up:
                        excel_mod = st.file_uploader("Subir Excel de Modificación", type=["xlsx", "xls"], key="mod_masiva", label_visibility="collapsed")

        st.divider()
        st.markdown("### 📋 Preguntas Actuales")

        if preguntas_existentes:
            for p in preguntas_existentes:
                q_id = p['id']
                with st.container(border=True):
                    if not st.session_state.get(f"edit_mode_{q_id}", False):
                        c1, c2, c3 = st.columns([0.7, 0.15, 0.15])
                        with c1:
                            st.markdown(
                                f"**{p['texto_pregunta']}** ({p['tipo_pregunta']})")
                            opciones = json.loads(p.get("opciones") or "[]")
                            if opciones:
                                st.caption("Opciones: " + ", ".join(opciones))
                        with c2:
                            if st.button("✏️ Editar",
                                         key=f"btn_edit_exist_{q_id}"):
                                st.session_state[f"edit_mode_{q_id}"] = True
                                st.session_state[f"edit_opciones_{q_id}"] = json.loads(
                                    p.get("opciones") or "[]")
                                st.session_state[f"edit_op_counter_{q_id}"] = 0
                                st.rerun()
                        with c3:
                            if st.button("🗑️ Eliminar",
                                         key=f"del_existente_{q_id}"):
                                eliminar_pregunta(q_id)
                                st.toast("Pregunta eliminada permanentemente.")
                                st.rerun()
                    else:
                        c1, c2 = st.columns([0.8, 0.2])
                        with c1:
                            st.markdown("**✏️ Editando Pregunta**")
                        with c2:
                            if st.button("❌ Cancelar",
                                         key=f"btn_cancel_edit_{q_id}"):
                                st.session_state[f"edit_mode_{q_id}"] = False
                                st.rerun()

                        nuevo_texto, nuevo_tipo, opciones_editar = render_question_builder_fields(
                            q_id, prefix="edit",
                            default_texto=p['texto_pregunta'],
                            default_tipo=p['tipo_pregunta'],
                            default_opciones=json.loads(
                                p.get("opciones") or "[]")
                        )

                        if st.button("💾 Guardar Cambios de Pregunta",
                                     type="primary", key=f"btn_save_edit_{q_id}"):
                            if not nuevo_texto.strip():
                                st.error(
                                    "El texto de la pregunta no puede estar vacío.")
                            elif nuevo_tipo in ["Opción única", "Opción múltiple"] and not opciones_editar:
                                st.error("Debes agregar al menos una opción.")
                            else:
                                editar_pregunta(
                                    q_id, nuevo_texto, nuevo_tipo, opciones_editar)
                                st.session_state[f"edit_mode_{q_id}"] = False
                                st.toast("Pregunta actualizada exitosamente.")
                                st.rerun()
        else:
            st.info("No hay preguntas en esta encuesta.")

        st.divider()
        st.markdown("### ➕ Añadir Nuevas Preguntas")

        if f"preguntas_nuevas_{encuesta_id}" not in st.session_state:
            st.session_state[f"preguntas_nuevas_{encuesta_id}"] = []

        preguntas_agregar = []

        for idx, q_id in enumerate(
                st.session_state[f"preguntas_nuevas_{encuesta_id}"]):
            with st.container(border=True):
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"**📝 Nueva Pregunta {idx + 1}**")
                with col2:
                    if st.button("🗑️ Quitar", key=f"del_nueva_{q_id}"):
                        st.session_state[f"preguntas_nuevas_{encuesta_id}"].remove(
                            q_id)
                        st.rerun()

                val_texto, val_tipo, opciones = render_question_builder_fields(
                    q_id, prefix="nueva")

                preguntas_agregar.append({
                    "texto": val_texto,
                    "tipo": val_tipo,
                    "opciones": opciones
                })

        if st.button("➕ Añadir otra pregunta"):
            st.session_state[f"preguntas_nuevas_{encuesta_id}"].append(str(uuid.uuid4()))
            st.rerun()

        st.divider()
        if st.button("💾 Guardar cambios", type="primary", use_container_width=True):
            import pandas as pd
            logo_base64_final = logo_actual
            if nuevo_logo_empresa:
                logo_base64_final = base64.b64encode(
                    nuevo_logo_empresa.getvalue()).decode("utf-8")

            # 1. Metadatos
            editar_metadata_encuesta(
                encuesta_id,
                titulo_nuevo,
                desc_nueva,
                empresa_dirigida_nueva,
                logo_base64_final,
                nueva_logo_position,
                nuevo_color_fondo)
                
            # 2. Nuevas preguntas
            if len(preguntas_agregar) > 0:
                hay_error = False
                for idx, p in enumerate(preguntas_agregar):
                    if not p["texto"].strip():
                        st.error(f"⚠️ La Nueva Pregunta {idx + 1} no tiene texto.")
                        hay_error = True
                    elif p["tipo"] in ["Opción única", "Opción múltiple"] and not p["opciones"]:
                        st.error(f"⚠️ La Nueva Pregunta {idx + 1} de opciones está vacía.")
                        hay_error = True
                
                if not hay_error:
                    agregar_nuevas_preguntas(encuesta_id, preguntas_agregar)
                    st.session_state[f"preguntas_nuevas_{encuesta_id}"] = []
                else:
                    return # Si hay error en preguntas, detenemos el guardado para que lo corrijan
                    
            # 3. Acciones de Padrón
            if "Privada" in enc.get("tipo_acceso", ""):
                df_padron_add = st.session_state.pop(
                    "edit_padron_df_mapped", None
                )
                mapping_json = st.session_state.pop(
                    "edit_padron_mapping_json", None
                )
                if df_padron_add is not None:
                    try:
                        agregar_padron(
                            encuesta_id,
                            df_padron_add,
                            variables_padron_json=mapping_json,
                        )
                    except Exception as e:
                        st.error(f"Error al procesar el padrón agregado: {e}")
                
                if excel_baja is not None:
                    try:
                        df_baja = pd.read_excel(excel_baja, header=None)
                        eliminar_colaboradores_masivo(encuesta_id, df_baja)
                    except Exception as e:
                        st.error(f"Error al procesar bajas masivas: {e}")
                        
                if excel_mod is not None:
                    try:
                        df_mod = pd.read_excel(excel_mod)
                        modificar_lideres_masivo(encuesta_id, df_mod)
                    except Exception as e:
                        st.error(f"Error al procesar modificación de líderes: {e}")

            st.toast("✅ Se realizaron todos los cambios exitosamente.")
            st.session_state.pop("editando_encuesta_id", None)
            st.rerun()
