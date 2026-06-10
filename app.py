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

from theme import inject_global_css

st.markdown(
    inject_global_css()
    + """
<style>
    .main { font-family: 'Inter', sans-serif; }
    h1 { font-weight: 800; text-align: center; margin-bottom: 20px; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea { border-radius: 8px; }
    hr {
        margin-top: 2rem; margin-bottom: 2rem; border: 0;
        border-top: 2px dashed rgba(148, 163, 184, 0.35);
    }
    .stButton>button {
        border-radius: 8px; font-weight: 600; transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
    }
    /* KPI del dashboard: misma altura y alineación superior */
    div[data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
    }
    div[data-testid="column"] {
        display: flex !important;
        flex-direction: column !important;
        align-self: stretch !important;
    }
    div[data-testid="column"] > div {
        flex: 1 1 auto !important;
        width: 100% !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        height: 100% !important;
        min-height: 148px !important;
        display: flex !important;
        flex-direction: column !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        flex: 1 1 auto !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
    }
    div[data-testid="stMetric"] {
        flex: 1 1 auto !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
        min-height: 108px !important;
    }
    div[data-testid="stMetricLabel"] {
        min-height: 1.5rem !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.1rem !important;
        font-weight: 800 !important;
    }
    /* Reserva espacio del badge en tarjetas sin delta (Padrón, Avance) */
    div[data-testid="stMetricDelta"] {
        min-height: 1.75rem !important;
    }
    div[data-testid="stMetric"]:not(:has([data-testid="stMetricDelta"])) [data-testid="stMetricValue"] {
        margin-bottom: 1.75rem !important;
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
            tab_crear, tab_lista = st.tabs(
                ["🎯 Crear Encuesta", "📂 Mis Encuestas"]
            )
            with tab_crear:
                render_crear_encuesta()
            with tab_lista:
                render_mis_encuestas()


if __name__ == "__main__":
    main()
