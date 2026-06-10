import streamlit as st
from bigquery_operations import (
    actualizar_estado_encuesta,
    obtener_todas_encuestas,
)


@st.cache_data(ttl=60, show_spinner=False)
def _cargar_lista_encuestas():
    return obtener_todas_encuestas()


def render_mis_encuestas():
    st.title("📂 Mis Encuestas")
    st.markdown(
        "Administra tus encuestas creadas. Activa o desactiva el acceso para los usuarios."
    )

    encuestas = None
    with st.spinner("Cargando encuestas desde BigQuery…"):
        try:
            encuestas = _cargar_lista_encuestas()
        except TimeoutError as err:
            st.error(str(err))
        except FileNotFoundError as err:
            st.error(str(err))
            st.info(
                "Coloca el archivo **credenciales.json** en la carpeta del proyecto "
                "o configura `st.secrets` para Streamlit Cloud."
            )
        except Exception as err:
            st.error(f"No se pudieron cargar las encuestas: {err}")

    if encuestas is None:
        if st.button("🔄 Reintentar conexión", type="primary"):
            _cargar_lista_encuestas.clear()
            st.rerun()
        return

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
                fecha = enc.get("fecha_creacion")
                tipo_acceso = enc.get("tipo_acceso", "Pública")
                badge = "🟢 Pública" if tipo_acceso == "Pública" else "🔒 Privada"

                if fecha:
                    st.caption(
                        f"Creada el: {fecha} &nbsp;&nbsp;|&nbsp;&nbsp; **{badge}**"
                    )
                else:
                    st.caption(f"**{badge}**")

                link = f"/?encuesta_id={enc.get('id')}"
                st.markdown(
                    f"**[🔗 Enlace de la encuesta]({link})** "
                    "(Botón derecho > Copiar enlace)"
                )
            with col2:
                estado_nuevo = st.toggle(
                    "Activa",
                    value=activa,
                    key=f"toggle_{enc.get('id')}",
                )
                if estado_nuevo != activa:
                    try:
                        actualizar_estado_encuesta(enc.get("id"), estado_nuevo)
                        _cargar_lista_encuestas.clear()
                        st.toast("✅ Estado actualizado")
                        st.rerun()
                    except Exception as err:
                        st.error(f"No se pudo actualizar el estado: {err}")

                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button(
                        "✏️ Editar",
                        key=f"edit_{enc.get('id')}",
                        use_container_width=True,
                    ):
                        st.session_state["editando_encuesta_id"] = enc.get("id")
                        st.rerun()
                with c_btn2:
                    if st.button(
                        "📊 Ver",
                        key=f"ver_{enc.get('id')}",
                        use_container_width=True,
                    ):
                        st.session_state["viendo_respuestas_id"] = enc.get("id")
                        st.rerun()
