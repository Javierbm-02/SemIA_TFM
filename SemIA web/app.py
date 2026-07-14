# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
SemIA Web — Backend Flask
Motor de predicción agrícola basado en Random Forest
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
import joblib
import os
import unicodedata
import re
import io

# ─────────────────────────────────────────────────────────────────────────────
# 1. Inicializar la aplicación Flask
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Configuración del modelo — local o GCP
#    Prioridad: variable de entorno MODEL_PATH → ruta local por defecto
# ─────────────────────────────────────────────────────────────────────────────
MODEL_GCS_URL = "https://storage.googleapis.com/unir-jbm/ML/componentes_semia_rf.pkl"

# Ruta local relativa al script (para desarrollo)
LOCAL_MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "componentes_semia_rf.pkl"
)

# Ruta del dataset (buscamos primero en la misma carpeta, luego en la superior)
DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset_eva_final.csv")
if not os.path.exists(DATASET_PATH):
    DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "dataset_eva_final.csv")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Cargar modelo y datos al arranque
# ─────────────────────────────────────────────────────────────────────────────
# Componentes del modelo (dict con 4 claves)
rf_model    = None   # RandomForestRegressor
rf_encoders = None   # dict de LabelEncoders por columna categórica
rf_scaler   = None   # StandardScaler
rf_cols     = None   # lista columnas_predictoras

df_global = None
municipios_por_depto = {}
all_municipios = []

def load_model():
    """Carga el modelo desde local o desde GCS y desempaqueta sus componentes."""
    global rf_model, rf_encoders, rf_scaler, rf_cols

    local_path = os.environ.get("MODEL_PATH", LOCAL_MODEL_PATH)
    if os.path.exists(local_path):
        print(f"Cargando modelo desde ruta local: {local_path}")
        obj = joblib.load(local_path)
    else:
        print(f"Descargando modelo desde GCS: {MODEL_GCS_URL}")
        try:
            import requests as req_lib
            response = req_lib.get(MODEL_GCS_URL, timeout=120)
            response.raise_for_status()
            obj = joblib.load(io.BytesIO(response.content))
        except Exception as e:
            print(f"Error al cargar modelo desde GCS: {e}")
            return

    # Desempaquetar el diccionario
    rf_model    = obj["modelo"]
    rf_encoders = obj["encoders"]          # dict: col -> LabelEncoder
    rf_scaler   = obj["scaler"]            # StandardScaler
    rf_cols     = obj["columnas_predictoras"]
    print("Modelo cargado. Columnas:", rf_cols)


def load_data():
    """Carga el dataset para extraer municipios y departamentos."""
    global df_global, municipios_por_depto, all_municipios

    if not os.path.exists(DATASET_PATH):
        print(f"⚠️  Dataset no encontrado en: {DATASET_PATH}")
        return

    print(f"📊 Cargando dataset desde: {DATASET_PATH}")
    df_global = pd.read_csv(DATASET_PATH, encoding='utf-8', low_memory=False)

    # Limpiar y preparar
    df_global["Municipio"]    = df_global["Municipio"].str.strip().str.upper()
    df_global["Departamento"] = df_global["Departamento"].str.strip().str.upper()

    # Construir diccionario Departamento → [Municipios]
    grouped = df_global.groupby("Departamento")["Municipio"].unique()
    for depto, municipios in grouped.items():
        municipios_por_depto[depto] = sorted(municipios.tolist())

    all_municipios = sorted(df_global["Municipio"].unique().tolist())
    print(f"✅ Dataset cargado: {len(df_global)} registros, "
          f"{len(all_municipios)} municipios, {len(municipios_por_depto)} departamentos.")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Función de normalización de texto
# ─────────────────────────────────────────────────────────────────────────────
def normalize(text: str) -> str:
    """Convierte a mayúsculas y elimina acentos."""
    if not isinstance(text, str):
        return ""
    text = text.upper().strip()
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def find_municipio(input_text: str):
    """Busca el municipio oficial a partir de un texto libre."""
    norm_input = normalize(input_text)
    for m in all_municipios:
        if normalize(m) == norm_input:
            return m
    # Búsqueda parcial
    for m in all_municipios:
        if norm_input in normalize(m) or normalize(m) in norm_input:
            return m
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Motor de recomendación SemIA
# ─────────────────────────────────────────────────────────────────────────────
def motor_recomendacion_semia(municipio_input: str, anio_input: int,
                               semestre_input: str, area_input: float, top_k: int = 5):
    """
    Genera el Top-K de cultivos recomendados para un municipio dado.
    El pkl es un dict con: modelo, encoders, scaler, columnas_predictoras.
    Columnas categóricas: Departamento, Municipio, Grupo_Cultivo, Cultivo, Semestre, Ciclo_Cultivo
    Columnas numéricas:   Anio, Area_Sembrada_ha
    """
    if rf_model is None or df_global is None:
        raise RuntimeError("El modelo o los datos no están disponibles.")

    municipio_oficial = find_municipio(municipio_input)
    if not municipio_oficial:
        raise ValueError(
            f"No encontré el municipio '{municipio_input}' en la base de datos. "
            "Verifique el nombre e intente de nuevo."
        )

    # Obtener departamento del municipio
    depto_row = df_global[df_global["Municipio"] == municipio_oficial]["Departamento"].iloc[0]

    # Obtener combinaciones únicas de Cultivo × Grupo × Ciclo en ese municipio
    cultivos_df = (
        df_global[df_global["Municipio"] == municipio_oficial][
            ["Cultivo", "Grupo_Cultivo", "Ciclo_Cultivo"]
        ]
        .drop_duplicates()
        .copy()
    )

    if cultivos_df.empty:
        raise ValueError(f"No hay datos de cultivos para '{municipio_oficial}'.")

    # Columnas categóricas y numéricas según el pkl
    cols_cat = ["Departamento", "Municipio", "Grupo_Cultivo", "Cultivo", "Semestre", "Ciclo_Cultivo"]
    cols_num = ["Anio", "Area_Sembrada_ha"]

    # Construir DataFrame de predicción
    rows = []
    for _, row in cultivos_df.iterrows():
        rows.append({
            "Departamento":    depto_row,
            "Municipio":       municipio_oficial,
            "Grupo_Cultivo":   row["Grupo_Cultivo"],
            "Cultivo":         row["Cultivo"],
            "Anio":            int(anio_input),
            "Semestre":        semestre_input.upper(),
            "Ciclo_Cultivo":   row["Ciclo_Cultivo"],
            "Area_Sembrada_ha": float(area_input),
        })

    X_pred = pd.DataFrame(rows, columns=rf_cols)

    # Aplicar LabelEncoders a columnas categóricas
    X_encoded = X_pred.copy()
    for col in cols_cat:
        le = rf_encoders.get(col)
        if le is None:
            continue
        known_classes = set(le.classes_)
        # Valores desconocidos → primera clase conocida del encoder
        X_encoded[col] = X_encoded[col].apply(
            lambda v: v if v in known_classes else le.classes_[0]
        )
        X_encoded[col] = le.transform(X_encoded[col].astype(str))

    # Escalar columnas numéricas
    X_encoded[cols_num] = rf_scaler.transform(X_encoded[cols_num])

    # Predicción con el RF
    preds = rf_model.predict(X_encoded[rf_cols])

    X_pred["Rendimiento_Proyectado_t_ha"] = preds
    X_pred["Produccion_Total_Estimada_t"] = preds * float(area_input)

    # Top-K
    top = (
        X_pred.sort_values("Rendimiento_Proyectado_t_ha", ascending=False)
        .head(top_k)
        .reset_index(drop=True)
    )

    return top[["Grupo_Cultivo", "Cultivo", "Ciclo_Cultivo",
                "Rendimiento_Proyectado_t_ha", "Produccion_Total_Estimada_t"]]



# ─────────────────────────────────────────────────────────────────────────────
# 6. Respuestas de small talk
# ─────────────────────────────────────────────────────────────────────────────
SMALL_TALK = {
    ("HOLA", "BUENOS DIAS", "BUENAS TARDES", "BUENAS NOCHES", "BUENAS"):
        "¡Hola! Soy **SemIA**, tu asistente de predicción agrícola. "
        "Puedo recomendarte los mejores cultivos para cualquier municipio de Colombia. "
        "¿Cómo te puedo ayudar?",

    ("COMO ESTAS", "COMO TE VA", "COMO VAS"):
        "¡Funcionando a pleno rendimiento! Listo para darte las mejores recomendaciones agrícolas. ¿En qué te puedo ayudar?",

    ("ADIOS", "CHAO", "HASTA LUEGO", "NOS VEMOS"):
        "¡Hasta pronto! Vuelve cuando necesites más recomendaciones agrícolas. 🌱",

    ("GRACIAS", "AGRADEZCO", "MUY AMABLE"):
        "¡De nada! Es un placer apoyar la agricultura colombiana. ¿Necesitas algo más?",

    ("QUIEN ERES", "QUE ERES", "PRESENTATE"):
        "Soy **SemIA**, un asistente de Inteligencia Artificial especializado en "
        "recomendaciones agrícolas para Colombia. Uso un modelo de Machine Learning "
        "entrenado con datos del Ministerio de Agricultura para predecir qué cultivos "
        "tienen mayor rendimiento en cada municipio.",

    ("QUE PUEDES HACER", "FUNCIONES", "PARA QUE SIRVES", "CAPACIDADES", "AYUDA", "HELP"):
        "Puedo:\n"
        "• 🌾 Recomendar los **Top 5 cultivos** con mayor rendimiento para tu municipio\n"
        "• 📅 Predecir por año y semestre (A=primer semestre, B=segundo semestre)\n"
        "• 📐 Estimar la producción total según el área que planeas sembrar\n\n"
        "Usa el formulario de la izquierda para hacer tu consulta.",

    ("COMO FUNCIONAS", "COMO TRABAJAS", "METODOLOGIA", "MODELO"):
        "Funciono con un **modelo Random Forest** entrenado con datos de Evaluaciones "
        "Agropecuarias Municipales (EVA) del MADR, cubriendo todo Colombia de 2007 a 2024. "
        "El modelo predice el **rendimiento en toneladas por hectárea** (t/ha) para cada cultivo.",

    ("DATOS", "FUENTE", "INFORMACION", "EVA"):
        "Mis datos provienen de las **Evaluaciones Agropecuarias Municipales (EVA)** del "
        "Ministerio de Agricultura y Desarrollo Rural de Colombia, con registros de 2007 a 2024.",

    ("CLIMA", "LLUVIA", "TEMPERATURA"):
        "No tengo acceso a datos meteorológicos. Mis predicciones se basan en patrones "
        "históricos de producción. Te recomiendo complementar con información climática local.",

    ("PRECIO", "MERCADO", "VENDER", "COSTO"):
        "No manejo información de precios ni mercados. Mi análisis se centra en el "
        "**rendimiento productivo** (t/ha). Para precios, consulta el SIPSA del DANE.",

    ("COLOMBIA", "BOLIVAR", "DEPARTAMENTO", "MUNICIPIO"):
        "Tengo datos de **todos los departamentos y municipios de Colombia** donde se "
        "han registrado evaluaciones agropecuarias. ¡Pregunta por cualquier municipio!",

    ("CHISTE", "BROMA"):
        "¿Por qué el maíz fue a terapia? ¡Porque se sentía muy desgranado! 🌽 "
        "Pero en serio, ¿necesitas una recomendación agrícola?",
}


def get_small_talk_response(user_input: str):
    """Busca una respuesta de small talk para la entrada del usuario."""
    norm = normalize(user_input)
    for keywords, response in SMALL_TALK.items():
        if any(kw in norm for kw in keywords):
            return response
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 7. Rutas Flask
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/municipios", methods=["GET"])
def get_municipios():
    """Devuelve los municipios agrupados por departamento."""
    return jsonify({
        "departamentos": municipios_por_depto,
        "total": len(all_municipios)
    })


@app.route("/api/recomendar", methods=["POST"])
def recomendar():
    """
    Endpoint principal de predicción.
    Body JSON: { municipio, anio, semestre, area, mensaje }
    """
    data = request.get_json(force=True)
    mensaje = data.get("mensaje", "").strip()

    # 1. Intentar small talk si hay un mensaje conversacional
    if mensaje and not data.get("municipio"):
        resp = get_small_talk_response(mensaje)
        if resp:
            return jsonify({"tipo": "conversacional", "respuesta": resp})
        # Si no es small talk y no hay datos de predicción → pedir datos
        return jsonify({
            "tipo": "conversacional",
            "respuesta": (
                "No entendí tu consulta. Para hacer una predicción, usa el formulario "
                "con municipio, año, semestre y área. ¿O tienes alguna pregunta sobre SemIA?"
            )
        })

    # 2. Predicción agrícola
    municipio = data.get("municipio", "").strip()
    anio      = data.get("anio")
    semestre  = data.get("semestre", "A").strip().upper()
    area      = data.get("area")

    # Validaciones
    if not municipio:
        return jsonify({"tipo": "error", "respuesta": "Por favor indica el municipio."}), 400
    if not anio:
        return jsonify({"tipo": "error", "respuesta": "Por favor indica el año."}), 400
    if not area:
        return jsonify({"tipo": "error", "respuesta": "Por favor indica el área en hectáreas."}), 400

    try:
        anio_int = int(anio)
        area_float = float(area)
    except (ValueError, TypeError):
        return jsonify({"tipo": "error", "respuesta": "Año o área con formato inválido."}), 400

    if semestre not in ("A", "B"):
        return jsonify({"tipo": "error", "respuesta": "El semestre debe ser 'A' o 'B'."}), 400

    try:
        resultado_df = motor_recomendacion_semia(municipio, anio_int, semestre, area_float)
        municipio_oficial = find_municipio(municipio)

        recomendaciones = resultado_df.to_dict(orient="records")
        return jsonify({
            "tipo": "prediccion",
            "municipio": municipio_oficial,
            "anio": anio_int,
            "semestre": semestre,
            "area": area_float,
            "recomendaciones": recomendaciones,
        })

    except ValueError as ve:
        return jsonify({"tipo": "error", "respuesta": str(ve)}), 404
    except RuntimeError as re_err:
        return jsonify({"tipo": "error", "respuesta": str(re_err)}), 503
    except Exception as e:
        return jsonify({"tipo": "error", "respuesta": f"Error interno: {str(e)}"}), 500


# ─────────────────────────────────────────────────────────────────────────────
# 8. Arranque
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    load_data()
    load_model()
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
else:
    # Para ejecución con gunicorn u otros WSGI
    load_data()
    load_model()
