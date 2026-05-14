import uuid
import json
import pandas as pd
from datetime import datetime
from google.cloud import bigquery
from google.oauth2 import service_account

# Credentials setup
CREDENTIALS_PATH = "credenciales.json"
PROJECT_ID = "sistema-consolidado-registro"
DATASET_ID = "sistema_encuestas"

import streamlit as st

def get_client():
    try:
        # Intentar leer desde st.secrets (para Streamlit Cloud)
        creds_info = dict(st.secrets["gcp_service_account"])
        credentials = service_account.Credentials.from_service_account_info(creds_info)
    except Exception:
        # Modo local: leer del archivo json
        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH)
    return bigquery.Client(credentials=credentials, project=PROJECT_ID)


def crear_encuesta(titulo, descripcion, preguntas, tipo_acceso="Pública", df_padron=None,
                   empresa_dirigida="", logo_empresa="", logo_position="Centro", color_fondo="#FFFFFF"):
    client = get_client()
    encuesta_id = str(uuid.uuid4())
    ahora = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")

    # 1. Insertar encuesta
    tabla_encuestas = f"{PROJECT_ID}.{DATASET_ID}.encuesta_info"
    rows_encuesta = [{"id": encuesta_id,
                      "titulo": titulo,
                      "descripcion": descripcion or "",
                      "fecha_creacion": ahora,
                      "activa": True,
                      "tipo_acceso": tipo_acceso,
                      "empresa_dirigida": empresa_dirigida,
                      "logo_empresa": logo_empresa,
                      "logo_position": logo_position,
                      "color_fondo": color_fondo,
                      "version_id": ahora}]
    client.load_table_from_json(
        rows_encuesta,
        tabla_encuestas,
        job_config=job_config).result()

    # 2. Guardar padrón si es privada
    if tipo_acceso and "Privada" in tipo_acceso and df_padron is not None:
        def normalize_col(c):
            c = str(c).strip().lower()
            if "dni lider" in c or "dni líder" in c:
                return "dni_lider_directo"
            if "lider directo" in c or "líder directo" in c:
                return "lider_directo"
            if "docu_iden" in c or "dni" in c:
                return "dni"
            if "nombre_completo" in c or "nombre" in c:
                return "nombre_completo"
            if "tienda" in c:
                return "tienda"
            if "orden" in c:
                return "orden_lider"
            return None

        new_cols = {}
        for c in df_padron.columns:
            nc = normalize_col(c)
            if nc:
                new_cols[c] = nc

        df_padron = df_padron.rename(columns=new_cols)

        # Fix: Drop any duplicated columns that resulted from multiple original columns mapping to the same target name
        df_padron = df_padron.loc[:, ~df_padron.columns.duplicated(keep='first')]

        # Ensure all columns exist
        expected_cols = [
            "dni",
            "nombre_completo",
            "tienda",
            "dni_lider_directo",
            "lider_directo",
            "orden_lider"]

        for col in expected_cols:
            if col not in df_padron.columns:
                df_padron[col] = ""

        df_padron = df_padron[expected_cols]

        text_cols = [
            "dni",
            "nombre_completo",
            "tienda",
            "dni_lider_directo",
            "lider_directo"]
        for col in text_cols:
            df_padron[col] = df_padron[col].fillna("").astype(str).str.replace(
                r'\.0$', '', regex=True).str.strip().replace({"nan": "", "NaT": "", "None": ""})

        # Convertir orden_lider a numérico
        df_padron["orden_lider"] = pd.to_numeric(
            df_padron["orden_lider"], errors="coerce")

        df_padron["encuesta_id"] = encuesta_id

        tabla_padron = f"{PROJECT_ID}.{DATASET_ID}.padron_encuestas"
        padron_job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
            schema_update_options=[
                bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
        )
        client.load_table_from_dataframe(
            df_padron, tabla_padron, job_config=padron_job_config).result()

    # 3. Insertar preguntas
    if preguntas:
        tabla_preguntas = f"{PROJECT_ID}.{DATASET_ID}.preguntas"
        rows_preguntas = []
        for idx, p in enumerate(preguntas):
            p_id = str(uuid.uuid4())
            rows_preguntas.append({
                "id": p_id,
                "encuesta_id": encuesta_id,
                "texto_pregunta": p["texto"],
                "tipo_pregunta": p["tipo"],
                "opciones": json.dumps(p.get("opciones", [])),
                "version_id": ahora,
                "orden": idx + 1
            })
        client.load_table_from_json(
            rows_preguntas,
            tabla_preguntas,
            job_config=job_config).result()

    return encuesta_id


def obtener_todas_encuestas():
    client = get_client()
    query = f"""
        SELECT
            e.id,
            e.titulo,
            e.descripcion,
            e.fecha_creacion,
            e.tipo_acceso,
            COALESCE(s.activa, TRUE) as activa
        FROM `{PROJECT_ID}.{DATASET_ID}.encuesta_info` as e
        LEFT JOIN (
            SELECT encuesta_id, activa
            FROM `{PROJECT_ID}.{DATASET_ID}.estado_encuestas`
            QUALIFY ROW_NUMBER() OVER (PARTITION BY encuesta_id ORDER BY fecha DESC) = 1
        ) as s
        ON e.id = s.encuesta_id
        QUALIFY ROW_NUMBER() OVER (PARTITION BY e.id ORDER BY e.fecha_creacion DESC) = 1
        ORDER BY e.fecha_creacion DESC
    """
    job_config = bigquery.QueryJobConfig(use_query_cache=False)
    df = client.query(query, job_config=job_config).to_dataframe()
    return df.to_dict('records')


def obtener_encuesta(encuesta_id):
    client = get_client()

    query_enc = f"""
        SELECT
            e.id,
            e.titulo,
            e.descripcion,
            e.fecha_creacion,
            e.tipo_acceso,
            e.empresa_dirigida,
            e.logo_empresa,
            e.logo_position,
            e.color_fondo,
            COALESCE(s.activa, TRUE) as activa
        FROM `{PROJECT_ID}.{DATASET_ID}.encuesta_info` as e
        LEFT JOIN (
            SELECT encuesta_id, activa
            FROM `{PROJECT_ID}.{DATASET_ID}.estado_encuestas`
            QUALIFY ROW_NUMBER() OVER (PARTITION BY encuesta_id ORDER BY fecha DESC) = 1
        ) as s
        ON e.id = s.encuesta_id
        WHERE e.id = @encuesta_id
        QUALIFY ROW_NUMBER() OVER (PARTITION BY e.id ORDER BY e.fecha_creacion DESC) = 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "encuesta_id",
                "STRING",
                encuesta_id)],
        use_query_cache=False
    )
    df_enc = client.query(query_enc, job_config=job_config).to_dataframe()
    if df_enc.empty:
        return None, []

    query_preg = f"""
        SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.preguntas`
        WHERE encuesta_id = @encuesta_id
        QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY COALESCE(version_id, '0') DESC) = 1
        ORDER BY COALESCE(orden, 999999) ASC, COALESCE(version_id, '0') ASC
    """
    df_preg = client.query(query_preg, job_config=job_config).to_dataframe()
    # Filter out logical soft-deleted questions
    df_preg = df_preg[df_preg['texto_pregunta'] != '__ELIMINADA__']

    encuesta = df_enc.iloc[0].to_dict()
    preguntas = df_preg.to_dict('records')
    return encuesta, preguntas


def actualizar_estado_encuesta(encuesta_id, estado_activo):
    client = get_client()
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    ahora = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")

    tabla_estados = f"{PROJECT_ID}.{DATASET_ID}.estado_encuestas"
    rows_estado = [{"encuesta_id": encuesta_id,
                    "activa": estado_activo, "fecha": ahora}]
    client.load_table_from_json(
        rows_estado,
        tabla_estados,
        job_config=job_config).result()


def obtener_padron(encuesta_id):
    client = get_client()
    query = f"""
        SELECT dni, nombre_completo, tienda, dni_lider_directo, lider_directo, orden_lider
        FROM `{PROJECT_ID}.{DATASET_ID}.padron_encuestas`
        WHERE encuesta_id = @encuesta_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("encuesta_id", "STRING", encuesta_id)
        ]
    )
    from google.api_core.exceptions import NotFound
    try:
        df = client.query(query, job_config=job_config).to_dataframe()
    except NotFound:
        return None
    if df.empty:
        return None
    return df


def validar_acceso_encuesta(encuesta_id, dni):
    client = get_client()
    query = f"""
        SELECT *
        FROM `{PROJECT_ID}.{DATASET_ID}.padron_encuestas`
        WHERE encuesta_id = @encuesta_id AND dni = @dni
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "encuesta_id", "STRING", encuesta_id),
            bigquery.ScalarQueryParameter("dni", "STRING", str(dni))
        ]
    )
    from google.api_core.exceptions import NotFound
    try:
        df = client.query(query, job_config=job_config).to_dataframe()
    except NotFound:
        return None

    if df.empty:
        return None
    return df.to_dict('records')


def obtener_lideres_evaluados(encuesta_id, dni):
    client = get_client()
    query = f"""
        SELECT DISTINCT r.lider_directo
        FROM `{PROJECT_ID}.{DATASET_ID}.respuestas` r
        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.respuestas_eliminadas` e ON r.id = e.id
        WHERE r.encuesta_id = @encuesta_id AND CAST(r.dni AS STRING) = @dni AND e.id IS NULL
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "encuesta_id", "STRING", encuesta_id),
            bigquery.ScalarQueryParameter("dni", "STRING", str(dni))
        ]
    )
    from google.api_core.exceptions import NotFound
    try:
        # Asegurar tabla eliminadas para que el JOIN no falle
        try:
            client.get_table(f"{PROJECT_ID}.{DATASET_ID}.respuestas_eliminadas")
        except NotFound:
            table = bigquery.Table(f"{PROJECT_ID}.{DATASET_ID}.respuestas_eliminadas", schema=[
                bigquery.SchemaField("id", "STRING"),
                bigquery.SchemaField("fecha", "STRING")
            ])
            client.create_table(table)

        df = client.query(query, job_config=job_config).to_dataframe()
    except NotFound:
        return []

    if df.empty:
        return []
    return df['lider_directo'].tolist()


def guardar_respuestas(encuesta_id, respuestas_dict, demographics=None):
    client = get_client()
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")

    respuesta_id = str(uuid.uuid4())
    ahora = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    base_respuesta = {
        "id": respuesta_id,
        "encuesta_id": encuesta_id,
        "fecha": ahora}
    if demographics:
        for k in ["dni", "nombre_completo", "tienda",
                  "dni_lider_directo", "lider_directo"]:
            base_respuesta[k] = str(demographics.get(k, ""))

        # Convertir orden_lider a numérico para la tabla de respuestas
        val_orden = demographics.get("orden_lider")
        try:
            base_respuesta["orden_lider"] = float(val_orden) if str(
                val_orden).strip() != "" and str(val_orden).lower() != "nan" else None
        except (ValueError, TypeError):
            base_respuesta["orden_lider"] = None

    tabla_respuestas = f"{PROJECT_ID}.{DATASET_ID}.respuestas"
    job_config_resp = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",
        schema_update_options=[
            bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
    )
    client.load_table_from_json(
        [base_respuesta],
        tabla_respuestas,
        job_config=job_config_resp).result()

    if respuestas_dict:
        tabla_detalle = f"{PROJECT_ID}.{DATASET_ID}.respuestas_detalle"
        rows_detalle = []
        for pregunta_id, respuesta_texto in respuestas_dict.items():
            if isinstance(respuesta_texto, list):
                respuesta_texto = ", ".join(respuesta_texto)
            rows_detalle.append({
                "id": str(uuid.uuid4()),
                "respuesta_id": respuesta_id,
                "pregunta_id": pregunta_id,
                "respuesta_texto": str(respuesta_texto)
            })
        client.load_table_from_json(
            rows_detalle,
            tabla_detalle,
            job_config=job_config)


def reiniciar_encuesta_usuario(encuesta_id, dni, lider_directo=None):
    client = get_client()
    try:
        # Primero obtenemos los IDs de las respuestas a eliminar
        query_ids = f"""
            SELECT id FROM `{PROJECT_ID}.{DATASET_ID}.respuestas`
            WHERE encuesta_id = @encuesta_id AND CAST(dni AS STRING) = @dni
        """
        params = [
            bigquery.ScalarQueryParameter("encuesta_id", "STRING", encuesta_id),
            bigquery.ScalarQueryParameter("dni", "STRING", str(dni))
        ]
        
        if lider_directo and lider_directo != "Todos":
            query_ids += " AND lider_directo = @lider"
            params.append(bigquery.ScalarQueryParameter("lider", "STRING", lider_directo))
            
        job_config_select = bigquery.QueryJobConfig(query_parameters=params)
        df_ids = client.query(query_ids, job_config=job_config_select).to_dataframe()
        
        if df_ids.empty:
            return False # No hay nada que borrar
            
        ids_to_delete = df_ids['id'].tolist()
        
        # Soft delete: Append to respuestas_eliminadas
        import datetime
        ahora = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        rows = [{"id": r_id, "fecha": ahora} for r_id in ids_to_delete]
        
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
            schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
        )
        client.load_table_from_json(
            rows,
            f"{PROJECT_ID}.{DATASET_ID}.respuestas_eliminadas",
            job_config=job_config
        ).result()
        
        return True
    except Exception as e:
        print(f"Error al reiniciar encuesta: {e}")
        return False


def editar_metadata_encuesta(encuesta_id, titulo, descripcion,
                             empresa_dirigida, logo_empresa, logo_position, color_fondo):
    client = get_client()
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    ahora = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")

    encuesta, _ = obtener_encuesta(encuesta_id)
    if not encuesta:
        return

    rows_encuesta = [{
        "id": encuesta_id,
        "titulo": titulo,
        "descripcion": descripcion or "",
        "fecha_creacion": ahora,
        "activa": True,
        "tipo_acceso": encuesta.get("tipo_acceso", "Pública"),
        "empresa_dirigida": empresa_dirigida,
        "logo_empresa": logo_empresa,
        "logo_position": logo_position,
        "color_fondo": color_fondo,
        "version_id": ahora
    }]
    tabla_encuestas = f"{PROJECT_ID}.{DATASET_ID}.encuesta_info"
    client.load_table_from_json(
        rows_encuesta,
        tabla_encuestas,
        job_config=job_config).result()


def eliminar_pregunta(pregunta_id):
    client = get_client()
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    ahora = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")

    query = f"SELECT encuesta_id, tipo_pregunta, opciones, orden FROM `{PROJECT_ID}.{DATASET_ID}.preguntas` WHERE id = @id LIMIT 1"
    job_cfg2 = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "id", "STRING", pregunta_id)])
    df = client.query(query, job_config=job_cfg2).to_dataframe()
    if df.empty:
        return
    enc_id = df.iloc[0]['encuesta_id']
    tipo = df.iloc[0]['tipo_pregunta']
    opciones = df.iloc[0]['opciones']
    orden = df.iloc[0]['orden']

    row = {
        "id": pregunta_id,
        "encuesta_id": enc_id,
        "texto_pregunta": "__ELIMINADA__",
        "tipo_pregunta": tipo,
        "opciones": opciones,
        "version_id": ahora,
        "orden": int(orden) if pd.notna(orden) else None
    }
    client.load_table_from_json(
        [row],
        f"{PROJECT_ID}.{DATASET_ID}.preguntas",
        job_config=job_config).result()


def editar_pregunta(pregunta_id, texto, tipo, opciones):
    client = get_client()
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    ahora = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")

    query = f"SELECT encuesta_id, orden FROM `{PROJECT_ID}.{DATASET_ID}.preguntas` WHERE id = @id LIMIT 1"
    job_cfg2 = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "id", "STRING", pregunta_id)])
    df = client.query(query, job_config=job_cfg2).to_dataframe()
    if df.empty:
        return
    enc_id = df.iloc[0]['encuesta_id']
    orden = df.iloc[0]['orden']

    row = {
        "id": pregunta_id,
        "encuesta_id": enc_id,
        "texto_pregunta": texto,
        "tipo_pregunta": tipo,
        "opciones": json.dumps(opciones),
        "version_id": ahora,
        "orden": int(orden) if pd.notna(orden) else None
    }
    client.load_table_from_json(
        [row],
        f"{PROJECT_ID}.{DATASET_ID}.preguntas",
        job_config=job_config).result()


def agregar_nuevas_preguntas(encuesta_id, preguntas):
    if not preguntas:
        return
    client = get_client()
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")

    query_max = f"""
        SELECT MAX(CAST(orden AS INT64)) as max_orden
        FROM `{PROJECT_ID}.{DATASET_ID}.preguntas`
        WHERE encuesta_id = @encuesta_id
    """
    df_max = client.query(query_max, job_config=bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "encuesta_id",
                "STRING",
                encuesta_id)]
    )).to_dataframe()

    max_orden = 0
    if not df_max.empty and pd.notna(df_max.iloc[0]['max_orden']):
        max_orden = int(df_max.iloc[0]['max_orden'])

    tabla_preguntas = f"{PROJECT_ID}.{DATASET_ID}.preguntas"
    rows_preguntas = []
    for idx, p in enumerate(preguntas):
        p_id = str(uuid.uuid4())
        rows_preguntas.append({
            "id": p_id,
            "encuesta_id": encuesta_id,
            "texto_pregunta": p["texto"],
            "tipo_pregunta": p["tipo"],
            "opciones": json.dumps(p.get("opciones", [])),
            "version_id": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f"),
            "orden": max_orden + idx + 1
        })
    client.load_table_from_json(
        rows_preguntas,
        tabla_preguntas,
        job_config=job_config).result()


def obtener_resultados(encuesta_id):
    client = get_client()
    query = f"""
        WITH padron AS (
            SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.padron_encuestas` WHERE encuesta_id = @encuesta_id
        ),
        resp as (
            SELECT r.* FROM `{PROJECT_ID}.{DATASET_ID}.respuestas` r
            LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.respuestas_eliminadas` e ON r.id = e.id
            WHERE r.encuesta_id = @encuesta_id AND e.id IS NULL
        )
        SELECT
            r.id as respuesta_id,
            r.fecha,
            COALESCE(pe.dni, CAST(r.dni AS STRING)) as dni,
            COALESCE(pe.nombre_completo, r.nombre_completo) as nombre_completo,
            COALESCE(pe.tienda, r.tienda) as tienda,
            COALESCE(pe.dni_lider_directo, r.dni_lider_directo) as dni_lider_directo,
            COALESCE(pe.lider_directo, r.lider_directo) as lider_directo,
            COALESCE(pe.orden_lider, CAST(r.orden_lider AS FLOAT64)) as orden_lider,
            CASE WHEN r.id IS NOT NULL THEN 1 ELSE 0 END as Ruta,
            p.texto_pregunta,
            d.respuesta_texto
        FROM padron pe
        FULL OUTER JOIN resp r
            ON pe.dni = CAST(r.dni AS STRING) AND COALESCE(pe.lider_directo, '') = COALESCE(r.lider_directo, '')
        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.respuestas_detalle` d ON r.id = d.respuesta_id
        LEFT JOIN (
            SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.preguntas`
            WHERE encuesta_id = @encuesta_id
            QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY COALESCE(version_id, '0') DESC) = 1
        ) p ON d.pregunta_id = p.id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("encuesta_id", "STRING", encuesta_id)
        ]
    )
    from google.api_core.exceptions import NotFound
    try:
        # Asegurar tabla eliminadas para que el JOIN no falle
        try:
            client.get_table(f"{PROJECT_ID}.{DATASET_ID}.respuestas_eliminadas")
        except NotFound:
            table = bigquery.Table(f"{PROJECT_ID}.{DATASET_ID}.respuestas_eliminadas", schema=[
                bigquery.SchemaField("id", "STRING"),
                bigquery.SchemaField("fecha", "STRING")
            ])
            client.create_table(table)

        df = client.query(query, job_config=job_config).to_dataframe()
    except NotFound:
        # Si las tablas padron_encuestas o respuestas no existen, retornar df vacío
        import pandas as pd
        df = pd.DataFrame()
    return df

def agregar_padron(encuesta_id, df_nuevo_padron):
    client = get_client()

    def normalize_col(c):
        c = str(c).strip().lower()
        if "dni lider" in c or "dni líder" in c:
            return "dni_lider_directo"
        if "lider directo" in c or "líder directo" in c:
            return "lider_directo"
        if "docu_iden" in c or "dni" in c:
            return "dni"
        if "nombre_completo" in c or "nombre" in c:
            return "nombre_completo"
        if "tienda" in c:
            return "tienda"
        if "orden" in c:
            return "orden_lider"
        return None

    new_cols = {}
    for c in df_nuevo_padron.columns:
        nc = normalize_col(c)
        if nc:
            new_cols[c] = nc

    df_nuevo_padron = df_nuevo_padron.rename(columns=new_cols)
    df_nuevo_padron = df_nuevo_padron.loc[:, ~df_nuevo_padron.columns.duplicated(keep='first')]

    expected_cols = [
        "dni",
        "nombre_completo",
        "tienda",
        "dni_lider_directo",
        "lider_directo",
        "orden_lider"]

    for col in expected_cols:
        if col not in df_nuevo_padron.columns:
            df_nuevo_padron[col] = ""

    df_nuevo_padron = df_nuevo_padron[expected_cols]

    text_cols = ["dni", "nombre_completo", "tienda", "dni_lider_directo", "lider_directo"]
    for col in text_cols:
        df_nuevo_padron[col] = df_nuevo_padron[col].fillna("").astype(str).str.replace(
            r'\.0$', '', regex=True).str.strip().replace({"nan": "", "NaT": "", "None": ""})

    df_nuevo_padron["orden_lider"] = pd.to_numeric(df_nuevo_padron["orden_lider"], errors="coerce")
    df_nuevo_padron["encuesta_id"] = encuesta_id

    df_actual = obtener_padron(encuesta_id)
    
    if df_actual is not None and not df_actual.empty:
        df_actual['clave_unica'] = df_actual['dni'].astype(str) + "_" + df_actual['lider_directo'].astype(str)
        df_nuevo_padron['clave_unica'] = df_nuevo_padron['dni'].astype(str) + "_" + df_nuevo_padron['lider_directo'].astype(str)
        
        df_a_insertar = df_nuevo_padron[~df_nuevo_padron['clave_unica'].isin(df_actual['clave_unica'])].copy()
        df_a_insertar = df_a_insertar.drop(columns=['clave_unica'])
    else:
        df_a_insertar = df_nuevo_padron
        
    agregados = len(df_a_insertar)
    ignorados = len(df_nuevo_padron) - agregados

    if agregados > 0:
        tabla_padron = f"{PROJECT_ID}.{DATASET_ID}.padron_encuestas"
        padron_job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
            schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
        )
        client.load_table_from_dataframe(df_a_insertar, tabla_padron, job_config=padron_job_config).result()
        
    return agregados, ignorados


def eliminar_colaboradores_masivo(encuesta_id, df_eliminar):
    client = get_client()
    
    # df_eliminar fue leido con header=None, así que la columna 0 tiene todos los datos
    dnis_raw = df_eliminar.iloc[:, 0].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().tolist()
    
    # Limpiamos posibles títulos que el usuario haya puesto en la fila 1
    dnis = []
    for d in dnis_raw:
        d_lower = d.lower()
        if d_lower not in ["", "nan", "none", "dni", "documento", "identificacion", "id"]:
            dnis.append(d)
    
    if not dnis:
        return 0
        
    # Leer todo el padron (como solucion al error 403 de DML en la capa gratuita)
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.padron_encuestas`"
    df_all = client.query(query).to_dataframe()
    
    if df_all.empty:
        return 0
        
    df_all['dni_str'] = df_all['dni'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    mask_to_delete = (df_all['encuesta_id'] == encuesta_id) & (df_all['dni_str'].isin(dnis))
    num_eliminados = mask_to_delete.sum()
    
    if num_eliminados == 0:
        return 0
        
    df_filtered = df_all[~mask_to_delete].copy()
    df_filtered = df_filtered.drop(columns=['dni_str'])
    
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    client.load_table_from_dataframe(df_filtered, f"{PROJECT_ID}.{DATASET_ID}.padron_encuestas", job_config=job_config).result()
    
    return int(num_eliminados)


def modificar_lideres_masivo(encuesta_id, df_modificacion):
    client = get_client()
    
    col_dni = None
    col_lider_anterior = None
    col_nuevo_lider = None
    
    for c in df_modificacion.columns:
        c_lower = str(c).lower()
        if "dni" in c_lower:
            col_dni = c
        elif "reemplazar" in c_lower or "anterior" in c_lower:
            col_lider_anterior = c
        elif "nuevo" in c_lower or "correcto" in c_lower:
            col_nuevo_lider = c
            
    if not col_dni or not col_nuevo_lider:
        raise ValueError("El Excel debe contener al menos las columnas para DNI y Nuevo Líder.")
        
    # Leer todo el padron (evitar DML)
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.padron_encuestas`"
    df_all = client.query(query).to_dataframe()
    
    if df_all.empty:
        return 0
        
    df_all['dni_str'] = df_all['dni'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    num_modificados = 0
    
    for _, row in df_modificacion.iterrows():
        dni = str(row[col_dni]).strip()
        if dni.endswith('.0'):
            dni = dni[:-2]
            
        if not dni or dni.lower() == "nan" or dni.lower() == "none":
            continue
            
        nuevo_lider = str(row[col_nuevo_lider]).strip()
        if not nuevo_lider or nuevo_lider.lower() == "nan":
            continue
            
        mask = (df_all['encuesta_id'] == encuesta_id) & (df_all['dni_str'] == dni)
        
        if col_lider_anterior and pd.notna(row[col_lider_anterior]) and str(row[col_lider_anterior]).strip() and str(row[col_lider_anterior]).strip().lower() != "nan":
            lider_anterior = str(row[col_lider_anterior]).strip()
            mask = mask & (df_all['lider_directo'].astype(str) == lider_anterior)
            
        if mask.sum() > 0:
            df_all.loc[mask, 'lider_directo'] = nuevo_lider
            num_modificados += mask.sum()
            
    if num_modificados == 0:
        return 0
        
    df_all = df_all.drop(columns=['dni_str'])
    
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    client.load_table_from_dataframe(df_all, f"{PROJECT_ID}.{DATASET_ID}.padron_encuestas", job_config=job_config).result()
    
    return int(num_modificados)


