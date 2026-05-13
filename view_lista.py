import streamlit as st
from bigquery_operations import obtener_todas_encuestas, actualizar_estado_encuesta


def render_mis_encuestas():
    st.title("📂 Mis Encuestas")
    st.markdown(
        "Administra tus encuestas creadas. Activa o desactiva el acceso para los usuarios.")

    encuestas = obtener_todas_encuestas()

    if not encuestas:
        st.info("Aún no has creado ninguna encuesta.")
        return

    for enc in encuestas:
        with st.container(border=True):
            col1, col2 = st.columns([0.7, 0.3])
            activa = enc.get("activa", True)
            if activa is None:
                activa = True

            with col1:
                st.subheader(enc.get("titulo", "Sin Título"))
                fecha = enc.get('fecha_creacion')
                tipo_acceso = enc.get('tipo_acceso', 'Pública')
                badge = "🟢 Pública" if tipo_acceso == 'Pública' else "🔒 Privada"

                if fecha:
                    st.caption(
                        f"Creada el: {fecha} &nbsp;&nbsp;|&nbsp;&nbsp; **{badge}**")
                else:
                    st.caption(f"**{badge}**")

                link = f"/?encuesta_id={enc.get('id')}"
                st.markdown(
                    f"**[🔗 Enlace de la encuesta]({link})** (Botón derecho > Copiar enlace)")
            with col2:
                estado_nuevo = st.toggle(
                    "Activa", value=activa, key=f"toggle_{
                        enc.get('id')}")
                if estado_nuevo != activa:
                    actualizar_estado_encuesta(enc.get("id"), estado_nuevo)
                    st.toast("✅ Estado actualizado")
                    st.rerun()

                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button(
                            "✏️ Editar", key=f"edit_{enc.get('id')}", use_container_width=True):
                        st.session_state["editando_encuesta_id"] = enc.get(
                            "id")
                        st.rerun()
                with c_btn2:
                    if st.button(
                            "📊 Ver", key=f"ver_{enc.get('id')}", use_container_width=True):
                        st.session_state["viendo_respuestas_id"] = enc.get(
                            "id")
                        st.rerun()
