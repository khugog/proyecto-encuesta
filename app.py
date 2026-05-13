import streamlit as st
from view_crear import render_crear_encuesta
from view_lista import render_mis_encuestas
from view_editar import render_editar_encuesta
from view_tomar import render_tomar_encuesta
from view_resultados import render_ver_respuestas

# Configuración de página
st.set_page_config(
    page_title="Plataforma de Encuestas",
    page_icon="🎯",
    layout="centered")

# CSS personalizado para la estética
st.markdown("""
<style>
    /* Estilos generales */
    .main {
        font-family: 'Inter', sans-serif;
    }
    h1 {
        font-weight: 800;
        text-align: center;
        margin-bottom: 20px;
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 8px;
    }
    /* Divider elegante */
    hr {
        margin-top: 2rem;
        margin-bottom: 2rem;
        border: 0;
        border-top: 2px dashed #d1d5db;
    }
    /* Alertas y botones */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Ruteo elegante mediante query params
    if "encuesta_id" in st.query_params:
        enc_id = st.query_params["encuesta_id"]
        render_tomar_encuesta(enc_id)
    else:
        if "editando_encuesta_id" in st.session_state:
            render_editar_encuesta(st.session_state["editando_encuesta_id"])
        elif "viendo_respuestas_id" in st.session_state:
            render_ver_respuestas(st.session_state["viendo_respuestas_id"])
        else:
            tab1, tab2 = st.tabs(["🎯 Crear Encuesta", "📂 Mis Encuestas"])
            with tab1:
                render_crear_encuesta()
            with tab2:
                render_mis_encuestas()


if __name__ == "__main__":
    main()
