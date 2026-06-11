"""Plantilla y mapeo de variables del padrón (DNI + variables configurables)."""

import io
import json
import re
import pandas as pd
import streamlit as st

# Columnas canónicas que ya existen en BigQuery
CANONICAL_FIELDS = {
    "dni": "dni",
    "nombre": "nombre_completo",
    "nombre_completo": "nombre_completo",
    "tienda": "tienda",
    "dni_lider": "dni_lider_directo",
    "dni_lider_directo": "dni_lider_directo",
    "lider": "lider_directo",
    "lider_directo": "lider_directo",
    "orden": "orden_lider",
    "orden_lider": "orden_lider",
}

MAX_VARIABLES = 50  # Aumentado para permitir más variables dinámicamente
PADRON_EXTRA_VARIABLES = 49  # Variable_2 … Variable_50 (la 1 es DNI)
SLOT_LABELS = [f"Variable_{i}" for i in range(1, MAX_VARIABLES + 1)]


def slugify(name: str) -> str:
    s = str(name).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "variable"


def build_default_mapping(excel_columns):
    """Sugiere mapeo según nombres de columnas del Excel - dinámico sin límite."""
    cols = [str(c).strip() for c in excel_columns]
    mapping = []
    used = set()

    def pick_col(keywords):
        for c in cols:
            cl = c.lower()
            if c in used:
                continue
            if any(k in cl for k in keywords):
                used.add(c)
                return c
        return None

    dni_col = pick_col(["dni", "docu", "documento", "identidad"]) or (
        cols[0] if cols else "Variable_1"
    )
    if dni_col not in used:
        used.add(dni_col)

    mapping.append({
        "slot": "variable_1",
        "columna_excel": dni_col,
        "nombre_interno": "dni",
        "etiqueta": "DNI",
        "obligatorio": True,
    })

    suggestions = [
        (["tienda", "local", "sucursal"], "tienda", "Tienda"),
        (["puesto", "cargo", "rol"], "puesto", "Puesto"),
        (["lider", "líder", "jefe"], "lider_directo", "Líder directo"),
        (["gerente", "zonal", "regional"], "gerente_zonal", "Gerente zonal"),
        (["genero", "género", "sexo"], "genero", "Género"),
        (["nombre"], "nombre_completo", "Nombre completo"),
    ]

    slot_idx = 2
    for keywords, interno, etiqueta in suggestions:
        col = pick_col(keywords)
        if col:
            mapping.append({
                "slot": f"variable_{slot_idx}",
                "columna_excel": col,
                "nombre_interno": interno,
                "etiqueta": etiqueta,
                "obligatorio": False,
            })
            slot_idx += 1

    # Procesar todas las columnas restantes sin límite
    for c in cols:
        if c in used:
            continue
        used.add(c)
        mapping.append({
            "slot": f"variable_{slot_idx}",
            "columna_excel": c,
            "nombre_interno": slugify(c),
            "etiqueta": c,
            "obligatorio": False,
        })
        slot_idx += 1

    return mapping


def render_padron_variable_mapper(df: pd.DataFrame, state_prefix: str = ""):
    """UI para asignar nombre a cada columna del Excel cargado."""
    st.markdown("#### 🏷️ Configurar variables del padrón")
    st.caption(
        "**Variable 1 = DNI** (obligatorio). Las variables adicionales se detectan "
        "automáticamente del Excel. Asigne nombres visibles (Tienda, Puesto, Líder, Género, etc.) "
        "para filtrar los gráficos de resultados."
    )

    map_key = f"{state_prefix}padron_variable_mapping"
    excel_cols = list(df.columns)
    
    # Regenerar mapeo si las columnas cambiaron
    if map_key not in st.session_state:
        st.session_state[map_key] = build_default_mapping(excel_cols)
    else:
        # Verificar si las columnas actuales coinciden con las del mapeo guardado
        saved_mapping = st.session_state[map_key]
        saved_cols = [item["columna_excel"] for item in saved_mapping]
        # Si las columnas son diferentes, regenerar el mapeo
        if set(saved_cols) != set(excel_cols):
            st.session_state[map_key] = build_default_mapping(excel_cols)

    mapping = st.session_state[map_key]

    updated = []
    for i, item in enumerate(mapping):
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 2])
            with c1:
                st.markdown(f"**{item['slot'].replace('_', ' ').title()}**")
                if item.get("obligatorio"):
                    st.caption("Obligatorio (DNI)")
            with c2:
                col_excel = st.selectbox(
                    "Columna en el archivo",
                    excel_cols,
                    index=excel_cols.index(item["columna_excel"])
                    if item["columna_excel"] in excel_cols
                    else 0,
                    key=f"map_col_{state_prefix}{i}",
                )
            with c3:
                etiqueta = st.text_input(
                    "Nombre visible (ej. Tienda, Puesto)",
                    value=item.get("etiqueta", ""),
                    key=f"map_lbl_{state_prefix}{i}",
                )
                interno = slugify(etiqueta) if etiqueta else slugify(col_excel)
                if item.get("obligatorio"):
                    interno = "dni"
                    etiqueta = etiqueta or "DNI"
            updated.append({
                "slot": item["slot"],
                "columna_excel": col_excel,
                "nombre_interno": interno,
                "etiqueta": etiqueta or col_excel,
                "obligatorio": item.get("obligatorio", False),
            })

    st.session_state[map_key] = updated
    return updated


def apply_padron_mapping(df: pd.DataFrame, mapping: list) -> pd.DataFrame:
    """Transforma el Excel cargado al formato del padrón + segmentación JSON."""
    out = pd.DataFrame()
    segmentacion_cols = {}

    for m in mapping:
        col_excel = m["columna_excel"]
        if col_excel not in df.columns:
            continue
        serie = df[col_excel].fillna("").astype(str).str.replace(
            r"\.0$", "", regex=True
        ).str.strip()
        interno = m["nombre_interno"]
        canon = CANONICAL_FIELDS.get(interno, interno)

        if canon in (
            "dni",
            "nombre_completo",
            "tienda",
            "dni_lider_directo",
            "lider_directo",
        ):
            out[canon] = serie
        elif canon == "orden_lider":
            out[canon] = pd.to_numeric(serie, errors="coerce")
        else:
            segmentacion_cols[m["etiqueta"]] = serie

    for col in (
        "dni",
        "nombre_completo",
        "tienda",
        "dni_lider_directo",
        "lider_directo",
        "orden_lider",
    ):
        if col not in out.columns:
            out[col] = "" if col != "orden_lider" else pd.NA

    if segmentacion_cols:
        seg_df = pd.DataFrame(segmentacion_cols)
        out["segmentacion"] = seg_df.apply(
            lambda r: json.dumps(
                {k: v for k, v in r.items() if str(v).strip()},
                ensure_ascii=False,
            ),
            axis=1,
        )
    else:
        out["segmentacion"] = "{}"

    return out


def mapping_to_json(mapping: list) -> str:
    return json.dumps(mapping, ensure_ascii=False)


def mapping_from_json(raw) -> list:
    if not raw:
        return []
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return []


def get_segment_dimensions(mapping: list, df_columns=None) -> list:
    """Dimensiones disponibles para cortar el dashboard de resultados."""
    dims = []
    seen = set()
    for m in mapping:
        etiqueta = m.get("etiqueta", "")
        interno = m.get("nombre_interno", "")
        canon = CANONICAL_FIELDS.get(interno)
        col = canon if canon and canon in (
            "tienda", "lider_directo", "nombre_completo", "dni_lider_directo"
        ) else None
        if col and col not in seen:
            dims.append({"columna": col, "etiqueta": etiqueta or col})
            seen.add(col)
        elif interno not in ("dni",) and etiqueta:
            key = f"seg_{slugify(etiqueta)}"
            if key not in seen:
                dims.append({"columna": key, "etiqueta": etiqueta, "from_json": True})
                seen.add(key)

    if df_columns is not None:
        cols = set(df_columns)
        for legacy, label in [
            ("tienda", "Tienda"),
            ("lider_directo", "Líder directo"),
            ("nombre_completo", "Nombre"),
        ]:
            if legacy in cols and legacy not in seen:
                dims.append({"columna": legacy, "etiqueta": label})
                seen.add(legacy)
        for c in cols:
            if c.startswith("seg_") and c not in seen:
                etiqueta = c.replace("seg_", "").replace("_", " ").title()
                dims.append({"columna": c, "etiqueta": etiqueta, "from_json": True})
                seen.add(c)

    return dims


def expand_segmentacion_column(df: pd.DataFrame) -> pd.DataFrame:
    """Añade columnas seg_* desde JSON de segmentación."""
    if "segmentacion" not in df.columns:
        return df
    rows = []
    for val in df["segmentacion"].fillna("{}"):
        try:
            rows.append(json.loads(val) if isinstance(val, str) else {})
        except json.JSONDecodeError:
            rows.append({})
    if not rows:
        return df
    seg_df = pd.DataFrame(rows)
    for c in seg_df.columns:
        df[f"seg_{slugify(c)}"] = seg_df[c]
    return df


def generate_padron_template_bytes() -> bytes:
    """Excel: Lee el archivo padron_de_variable.xlsx existente."""
    try:
        with open("padron_de_variable.xlsx", "rb") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback si no existe el archivo
        headers = ["DNI", "Variable_2", "Variable_3", "Variable_4", "Variable_5"]
        ejemplo = {
            "DNI": ["12345678", "87654321"],
            "Variable_2": ["Tienda Centro", "Tienda Norte"],
            "Variable_3": ["Cajero", "Supervisor"],
            "Variable_4": ["Juan Pérez", "María López"],
            "Variable_5": ["Masculino", "Femenino"],
        }
        df = pd.DataFrame({h: ejemplo.get(h, ["", ""]) for h in headers})
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Padron")
        return buf.getvalue()


def generate_padron_lider_template_bytes() -> bytes:
    """Excel: Lee el archivo plantilla_padron.xlsx existente."""
    try:
        with open("plantilla_padron.xlsx", "rb") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback si no existe el archivo
        headers = ["DNI", "Nombre Completo", "Líder Directo"]
        ejemplo = {
            "DNI": ["12345678", "87654321", "11223344"],
            "Nombre Completo": ["Juan Pérez García", "María López Sánchez", "Carlos Rodríguez Méndez"],
            "Líder Directo": ["Ana Martínez", "Pedro Gómez", "Ana Martínez"],
        }
        df = pd.DataFrame({h: ejemplo.get(h, ["", ""]) for h in headers})
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Padron")
        return buf.getvalue()
