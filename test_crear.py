import pandas as pd
import traceback
from bigquery_operations import crear_encuesta

df = pd.DataFrame({
    'dni': ['13579111'],
    'nombre_completo': ['Test User'],
    'tienda': ['Store 1'],
    'dni_lider_directo': ['12345678'],
    'lider_directo': ['Lider Test'],
    'orden_lider': [1]
})

preguntas = [{"texto": "Pregunta 1", "tipo": "Texto libre"}]

try:
    enc_id = crear_encuesta(
        titulo="Test Privada",
        descripcion="Test",
        preguntas=preguntas,
        tipo_acceso="Privada",
        df_padron=df
    )
    print("Success. Encuesta ID:", enc_id)
except Exception as e:
    traceback.print_exc()
