import streamlit as st
import pandas as pd
from bigquery_operations import obtener_encuesta, obtener_resultados, reiniciar_encuesta_usuario


def render_ver_respuestas(encuesta_id):
    st.button(
        "⬅️ Volver a Mis Encuestas",
        on_click=lambda: st.session_state.pop(
            "viendo_respuestas_id",
            None))

    enc, preguntas = obtener_encuesta(encuesta_id)
    df_resultados = obtener_resultados(encuesta_id)

    if not enc:
        st.error("No se encontró la encuesta.")
        return

    st.title(f"📊 Resultados: {enc.get('titulo', 'Sin Título')}")

    tipo_acceso = enc.get('tipo_acceso', 'Pública')
    badge = "🟢 Pública" if tipo_acceso == 'Pública' else "🔒 Privada"
    empresa = enc.get('empresa_dirigida', 'No especificada')

    st.markdown(
        f"**Tipo de Acceso:** {badge} &nbsp;|&nbsp; **Empresa:** 🏢 {empresa}")

    if enc.get('descripcion'):
        st.caption(f"{enc.get('descripcion')}")
    st.divider()

    if df_resultados.empty:
        st.info("Aún no hay respuestas para esta encuesta.")
    else:

        # Transformar a formato ancho (una fila por usuario, columnas por
        # pregunta)

        # FIX: Evitar error de pandas "Cannot interpret 'datetime64[us, UTC]'
        # as a data type" en pivot_table
        for col in df_resultados.columns:
            if pd.api.types.is_datetime64_any_dtype(df_resultados[col]):
                df_resultados[col] = df_resultados[col].dt.strftime(
                    '%Y-%m-%d %H:%M:%S')

        # Ocultar TODOS los datos demográficos si la encuesta es PÚBLICA
        if enc.get('tipo_acceso') == 'Pública':
            # Mantenemos estrictamente solo los datos de la respuesta y las
            # preguntas
            columnas_permitidas = [
                'respuesta_id',
                'fecha',
                'fecha_respuesta',
                'texto_pregunta',
                'respuesta_texto',
                'Ruta']
            cols_a_mantener = [
                c for c in columnas_permitidas if c in df_resultados.columns]
            df_resultados = df_resultados[cols_a_mantener]

        index_cols = [
            c for c in df_resultados.columns if c not in [
                'texto_pregunta',
                'respuesta_texto']]

        # Extraer la base de encuestados (incluyendo los de Ruta=0)
        df_base = df_resultados[index_cols].drop_duplicates()

        # Filtrar solo los que tienen respuestas a preguntas
        df_valid = df_resultados.dropna(subset=['texto_pregunta']).copy()

        # FIX: Evitar que pandas elimine encuestados si dejaron algún campo
        # demográfico vacío
        for col in index_cols:
            if col in df_base.columns:
                df_base[col] = df_base[col].fillna("No especificado")
            if col in df_valid.columns:
                df_valid[col] = df_valid[col].fillna("No especificado")

        if not df_valid.empty:
            df_pivot = df_valid.pivot_table(
                index=index_cols,
                columns='texto_pregunta',
                values='respuesta_texto',
                aggfunc=lambda x: ', '.join(str(v) for v in x.dropna())
            ).reset_index()
            df_pivot.columns.name = None

            # Asegurar que todos los encuestados estén presentes (incluso
            # Ruta=0)
            df_pivot = pd.merge(df_base, df_pivot, on=index_cols, how='left')
        else:
            df_pivot = df_base

        # Ocultar la columna de IDs internos para que el usuario no la vea de
        # forma innecesaria
        if 'respuesta_id' in df_pivot.columns:
            df_pivot = df_pivot.drop(columns=['respuesta_id'])

        try:
            from theme import show_plotly_chart
        except ImportError:
            show_plotly_chart = None
        try:
            from dashboard_charts import (
                build_participation_donut,
                build_participation_gauge,
                render_private_kpi_metrics,
                render_public_kpi_metrics,
            )
        except ImportError:
            pass
        try:
            from dashboard_results import render_results_dashboard
        except ImportError:
            pass
        # Padrón functionality temporarily disabled
        var_mapping = None
        segment_dims = None

        tab_part, tab_res = st.tabs([
            "📈 Participación",
            "🎯 Resultados (Scores)",
        ])

        with tab_part:
            st.markdown("### Dashboard de Participación")

            if enc.get('tipo_acceso') == 'Pública':
                total_respuestas = df_resultados['respuesta_id'].nunique()
                render_public_kpi_metrics(total_respuestas, df_resultados)
            else:
                total_esperado = len(df_base)
                total_respuestas = df_base[
                    pd.to_numeric(df_base['Ruta'], errors='coerce') == 1
                ].shape[0]
                faltantes = total_esperado - total_respuestas
                porcentaje = (
                    (total_respuestas / total_esperado * 100)
                    if total_esperado > 0
                    else 0
                )

                render_private_kpi_metrics(
                    total_esperado, total_respuestas, faltantes, porcentaje
                )

                if total_esperado > 0:
                    st.progress(
                        min(porcentaje / 100, 1.0),
                        text=(
                            f"{total_respuestas} de {total_esperado} "
                            "evaluaciones completadas"
                        ),
                    )

                    c_donut, c_gauge = st.columns(2)
                    with c_donut:
                        show_plotly_chart(
                            build_participation_donut(
                                total_respuestas, faltantes, porcentaje
                            ),
                        )
                    with c_gauge:
                        show_plotly_chart(build_participation_gauge(porcentaje))

        with tab_res:
            st.markdown("### Dashboard de Resultados")
            st.caption(
                "Scores de liderazgo (Likert) y NPS por pregunta. "
                "Filtra por las variables del padrón (tienda, puesto, etc.)."
            )
            render_results_dashboard(
                df_resultados,
                preguntas,
                df_base,
                segment_dims,
                var_mapping=var_mapping,
            )

        st.divider()
        st.markdown("### 📋 Datos Detallados")

        st.dataframe(df_pivot, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_down1, col_down2 = st.columns(2)
        
        import io
        
        with col_down1:
            # Botón de descarga Excel de todos
            buffer_todos = io.BytesIO()
            with pd.ExcelWriter(buffer_todos, engine='openpyxl') as writer:
                df_pivot.to_excel(writer, index=False, sheet_name='Resultados')
            
            st.download_button(
                label="⬇️ Descargar TODOS los resultados",
                data=buffer_todos.getvalue(),
                file_name=f"resultados_{enc.get('titulo', 'encuesta')}.xlsx",
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                type="primary",
                use_container_width=True
            )
            
        with col_down2:
            if enc.get('tipo_acceso') != 'Pública' and 'Ruta' in df_pivot.columns:
                df_pendientes = df_pivot[pd.to_numeric(df_pivot['Ruta'], errors='coerce') == 0].copy()
                if 'respuesta_id' in index_cols:
                    index_cols.remove('respuesta_id')
                df_pendientes = df_pendientes[[c for c in index_cols if c in df_pendientes.columns]]
                
                if df_pendientes.empty:
                    st.success("🎉 ¡Todos han completado la encuesta!")
                else:
                    buffer_pendientes = io.BytesIO()
                    with pd.ExcelWriter(buffer_pendientes, engine='openpyxl') as writer:
                        df_pendientes.to_excel(writer, index=False, sheet_name='Pendientes')
                    
                    st.download_button(
                        label="⬇️ Descargar PENDIENTES",
                        data=buffer_pendientes.getvalue(),
                        file_name=f"pendientes_{enc.get('titulo', 'encuesta')}.xlsx",
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        type="secondary",
                        help="Descargar un archivo solo con los colaboradores que aún no han completado la encuesta.",
                        use_container_width=True
                    )

        if enc.get('tipo_acceso') != 'Pública':
            st.divider()
            st.markdown("### 🔄 Reiniciar Evaluación de Usuario")
            st.info("Si un usuario se equivocó y completó la encuesta, ingresa su DNI para borrar sus respuestas. Su registro seguirá apareciendo en la lista pero su columna 'Ruta' cambiará a 0 y podrá volver a realizar la encuesta.")
            
            with st.form("reset_form"):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    dni_reset = st.text_input("DNI del participante")
                with col2:
                    # Mostrar líderes si aplica
                    lideres_opt = ["Todos"]
                    if 'lider_directo' in df_base.columns:
                        lideres_opt += sorted(df_base['lider_directo'].dropna().unique().tolist())
                    lider_reset = st.selectbox("Líder Evaluado a reiniciar", lideres_opt, help="Si seleccionas 'Todos', se reiniciarán todas las evaluaciones de este DNI.")
                with col3:
                    st.write("")
                    st.write("")
                    btn_reset = st.form_submit_button("Reiniciar Encuesta")
                    
                if btn_reset:
                    if dni_reset:
                        if reiniciar_encuesta_usuario(encuesta_id, dni_reset.strip(), lider_reset):
                            st.success(f"✅ Se han eliminado las respuestas del DNI {dni_reset}. Su ruta volverá a 0.")
                            st.rerun()
                        else:
                            st.error(f"❌ No se encontraron respuestas válidas para borrar con el DNI {dni_reset}.")
                    else:
                        st.warning("⚠️ Debes ingresar un DNI.")
