# 🌾 SemIA Web — Sistema de Predicción Agrícola con IA

> **Módulo de aplicación web del Trabajo de Fin de Máster (TFM)**
> Universidad Internacional de La Rioja (UNIR) · 2025
> Autor: Jorge Benjumea Medina

---

## 📋 Descripción General

**SemIA** *(Siembra + IA)* es una aplicación web de predicción agrícola que usa Machine Learning para recomendar los cultivos con mayor rendimiento esperado en cualquier municipio de Colombia, dado un año, semestre y área a sembrar.

El sistema fue entrenado con datos del **Ministerio de Agricultura y Desarrollo Rural (MADR)** — Evaluaciones Agropecuarias Municipales (EVA) — de 2007 a 2024, con más de **351.920 registros** y cobertura de los **32 departamentos** y **1.061 municipios** de Colombia.

La aplicación no requiere login ni registro. El usuario interactúa directamente con el predictor integrado en la landing page.

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLIENTE (Navegador)                         │
│   HTML · CSS (Verde Agricultura) · JavaScript (main.js)          │
│   Secciones: Navbar · Hero · Features · Stats · Dashboard        │
│              Predictor/Chatbot · Footer                          │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP / AJAX (fetch API)
┌────────────────────────▼────────────────────────────────────────┐
│                  BACKEND Flask  (app.py — puerto 5001)           │
│                                                                  │
│  GET  /                  → Sirve index.html (Jinja2)             │
│  GET  /api/municipios    → JSON lista de deptos + municipios     │
│  POST /api/recomendar    → JSON Top-5 cultivos o small talk      │
└──────────┬───────────────────────────────┬───────────────────── ┘
           │                               │
  ┌────────▼──────────┐       ┌────────────▼──────────────────┐
  │ dataset_eva_      │       │  componentes_semia_rf.pkl       │
  │ final.csv         │       │  ├── modelo  (RF Regressor)     │
  │ 351.920 filas     │       │  ├── encoders (LabelEncoder x6) │
  │ (menús dinámicos) │       │  ├── scaler  (StandardScaler)   │
  └───────────────────┘       │  └── columnas_predictoras       │
                              └───────────────────────────────┘
                                  Local → fallback GCS
```

---

## 🧠 Modelo de Machine Learning

### Algoritmo: Random Forest Regressor

El archivo `componentes_semia_rf.pkl` no es un pipeline directo — es un **diccionario** con 4 componentes que deben aplicarse manualmente en el orden correcto:

| Clave | Tipo | Descripción |
|---|---|---|
| `modelo` | `RandomForestRegressor` | Modelo entrenado con sklearn 1.5.1 |
| `encoders` | `dict[str → LabelEncoder]` | Un encoder por cada columna categórica |
| `scaler` | `StandardScaler` | Escala las columnas numéricas |
| `columnas_predictoras` | `list[str]` | Orden exacto de features requerido por el RF |

### Features de entrada

| Feature | Tipo | Preprocesado |
|---|---|---|
| `Departamento` | Categórica | LabelEncoder |
| `Municipio` | Categórica | LabelEncoder |
| `Grupo_Cultivo` | Categórica | LabelEncoder |
| `Cultivo` | Categórica | LabelEncoder |
| `Semestre` | Categórica (A / B) | LabelEncoder |
| `Ciclo_Cultivo` | Categórica | LabelEncoder |
| `Anio` | Numérica | StandardScaler |
| `Area_Sembrada_ha` | Numérica | StandardScaler |

**Variable objetivo (target):** `Rendimiento_t_ha` — toneladas producidas por hectárea sembrada.

### Flujo de inferencia (app.py)

```python
# 1. Obtener combinaciones únicas Cultivo × Grupo × Ciclo del municipio
cultivos_df = df[df["Municipio"] == municipio][
    ["Cultivo", "Grupo_Cultivo", "Ciclo_Cultivo"]
].drop_duplicates()

# 2. Construir DataFrame con los 8 features
X_pred = pd.DataFrame(rows, columns=rf_cols)

# 3. Aplicar LabelEncoder por columna categórica
for col in cols_cat:
    le = rf_encoders[col]
    X_encoded[col] = le.transform(X_encoded[col])

# 4. Escalar columnas numéricas
X_encoded[cols_num] = rf_scaler.transform(X_encoded[cols_num])

# 5. Predecir y retornar Top-5 por rendimiento descendente
preds = rf_model.predict(X_encoded[rf_cols])
top5 = X_pred.assign(rend=preds).sort_values("rend", ascending=False).head(5)
```

> ⚠️ **Advertencia de versión:** El modelo fue entrenado con `scikit-learn==1.5.1`.
> Al usarlo con versiones superiores (1.9.x) aparecen `InconsistentVersionWarning`.
> El modelo **funciona correctamente** a pesar del warning.
> Para producción se recomienda fijar `scikit-learn==1.5.1`.

---

## 📁 Estructura de Archivos

```
TFM/
├── SemIA web/                       ← Esta aplicación web
│   ├── README.md                    ← Este documento
│   ├── app.py                       ← Backend Flask (375 líneas)
│   ├── requirements.txt             ← Dependencias Python
│   ├── test_model.py                ← Script de prueba de inferencia
│   ├── templates/
│   │   └── index.html               ← SPA (377 líneas): toda la UI
│   └── static/
│       ├── css/
│       │   └── style.css            ← Sistema de diseño (~700 líneas)
│       ├── js/
│       │   └── main.js              ← Lógica del chatbot (~340 líneas)
│       └── img/
│           ├── logo.png
│           └── cultivo.webp
│
├── componentes_semia_rf.pkl         ← Modelo ML (≈ 357 MB)
├── dataset_eva_final.csv            ← Datos EVA 2007-2024 (351.920 filas)
├── SemIA_ML.ipynb                   ← Notebook de entrenamiento
└── backend/                         ← Versión anterior del proyecto
```

---

## 🎨 Sistema de Diseño

### Paleta "Verde Agricultura"

```css
--verde:       #28A745   /* Principal: botones, iconos, navbar */
--verde-dark:  #1e7e34   /* Hover states, headers             */
--verde-soft:  #C8E6C9   /* Badges, chips                     */
--verde-pale:  #e8f5e9   /* Fondos de sección, chat bubbles   */
--dorado:      #FFC107   /* Acentos CTA, rank #1              */
--dorado-dark: #e6a800   /* Hover del dorado                  */
--azul-dark:   #003366   /* Gradiente hero, textos oscuros    */
```

### Tipografía

- **Outfit** (Google Fonts) — pesos 300, 400, 500, 600, 700, 800
- Fallback: `'Segoe UI', sans-serif`

### Componentes principales

| Componente | Archivo | Descripción |
|---|---|---|
| Navbar fijo | `style.css` | Glassmorphism verde, scroll shadow, hamburger |
| Hero | `style.css` | Gradiente diagonal, stats flotantes con animación float |
| Feature cards | `style.css` | Hover lift + borde gradiente animado |
| Stats animados | `main.js` | Intersection Observer + contador incremental |
| Chat window | `style.css` | Bubbles verde/dorado, typing dots, scroll suave |
| Result table | `style.css` | Badges de ranking oro/plata/bronce, hover rows |

---

## 🚀 Instalación y Ejecución Local

### Prerrequisitos

- Python 3.9 o superior (probado con Python 3.14.4)
- Archivos en la carpeta `TFM/`:
  - `componentes_semia_rf.pkl` (modelo, ~357 MB)
  - `dataset_eva_final.csv` (dataset, ~45 MB)

### Paso 1 — Instalar dependencias

```bash
cd "d:\Mi_repos\AgroIA\TFM\SemIA web"
pip install -r requirements.txt
```

Dependencias instaladas:
```
flask>=2.3.0
flask-cors>=4.0.0
pandas>=2.0.0
joblib>=1.3.0
scikit-learn>=1.3.0
numpy>=1.24.0
requests>=2.31.0
```

### Paso 2 — Ejecutar el servidor

```powershell
# Windows (PowerShell) — necesario para emojis en consola
$env:PYTHONIOENCODING="utf-8"
python app.py
```

```bash
# Linux / macOS
PYTHONIOENCODING=utf-8 python app.py
```

### Paso 3 — Abrir en el navegador

```
http://localhost:5001
```

> **Tiempos de arranque esperados:**
> - Dataset 351K filas: ~5 segundos
> - Modelo RF (~357 MB): ~15 segundos
> Total: ~20 segundos hasta "Running on http://127.0.0.1:5001"

### Paso 4 — Verificar inferencia

```bash
python test_model.py
```

Salida esperada:
```
TOP 5 CUMARIBO 2026-A:
  PATILLA                   11.58 t/ha
  Maracuyá                  11.52 t/ha
  TOMATE                    11.19 t/ha
  Caña                      11.05 t/ha
  YUCA                      11.04 t/ha
OK - inferencia exitosa
```

---

## 🌐 Referencia de la API

### `GET /`
Sirve la aplicación web completa (`index.html`).

---

### `GET /api/municipios`

Retorna todos los departamentos y sus municipios disponibles en el dataset.

**Respuesta `200 OK`:**
```json
{
  "departamentos": {
    "AMAZONAS": ["LETICIA", "PUERTO NARIÑO"],
    "ANTIOQUIA": ["ABEJORRAL", "ABRIAQUÍ", "ALEJANDRÍA"],
    "...": "..."
  },
  "total": 1061
}
```

---

### `POST /api/recomendar`

Endpoint principal. Acepta dos modos:

#### Modo predicción agrícola

```json
{
  "municipio": "CUMARIBO",
  "anio": 2026,
  "semestre": "A",
  "area": 10.0
}
```

**Respuesta `200 OK`:**
```json
{
  "tipo": "prediccion",
  "municipio": "CUMARIBO",
  "anio": 2026,
  "semestre": "A",
  "area": 10.0,
  "recomendaciones": [
    {
      "Cultivo": "PATILLA",
      "Grupo_Cultivo": "FRUTALES",
      "Ciclo_Cultivo": "TRANSITORIO",
      "Rendimiento_Proyectado_t_ha": 11.58,
      "Produccion_Total_Estimada_t": 115.85
    }
  ]
}
```

#### Modo small talk / conversacional

```json
{ "mensaje": "¿Quién eres?" }
```

**Respuesta `200 OK`:**
```json
{
  "tipo": "conversacional",
  "respuesta": "Soy **SemIA**, tu asistente de predicción agrícola..."
}
```

**Códigos de error:**

| Código | Situación |
|---|---|
| `400` | Parámetros faltantes o municipio no encontrado |
| `503` | Modelo no disponible (falló la carga) |
| `500` | Error interno en la inferencia |

---

## ☁️ Despliegue en Google Cloud Platform

### Opción 1 — Cloud Run (recomendada para producción)

**1. Crear `Dockerfile`** *(pendiente — ver sección de pendientes)*:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONIOENCODING=utf-8
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app
```

**2. Build y deploy:**
```bash
gcloud builds submit --tag gcr.io/[PROJECT_ID]/semia-web
gcloud run deploy semia-web \
  --image gcr.io/[PROJECT_ID]/semia-web \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --set-env-vars PYTHONIOENCODING=utf-8
```

### Opción 2 — App Engine

```yaml
# app.yaml
runtime: python311
entrypoint: gunicorn -b :$PORT app:app

env_variables:
  PYTHONIOENCODING: "utf-8"

resources:
  memory_gb: 4
  disk_size_gb: 10
```

### Modelo en GCS

En producción, si el modelo no está en el sistema de archivos local, el backend lo descarga automáticamente desde GCS.

Para habilitar acceso público al objeto:
```bash
gsutil acl ch -u AllUsers:R gs://unir-jbm/ML/componentes_semia_rf.pkl
```

URL de descarga (hardcodeada como fallback en `app.py`):
```
https://storage.googleapis.com/unir-jbm/ML/componentes_semia_rf.pkl
```

---

## ⚙️ Variables de Entorno

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `MODEL_PATH` | `../componentes_semia_rf.pkl` | Ruta local al modelo. Vacío = descarga de GCS |
| `PYTHONIOENCODING` | — | Configurar a `utf-8` en Windows |
| `PORT` | `5001` | Puerto del servidor. Cloud Run usa `$PORT` automáticamente |
| `FLASK_ENV` | `development` | `production` desactiva el debugger de Werkzeug |

---

## 🔄 Comparación con el Módulo Anterior (`backend/`)

| Característica | AgroIA v1 (`backend/`) | SemIA Web (`TFM/SemIA web/`) |
|---|---|---|
| Login requerido | ✅ Sí | ❌ No — acceso libre |
| Cobertura | Solo Bolívar | 32 departamentos, 1.061 municipios |
| Chatbot | Página separada | Integrado en la landing page |
| Dashboard | Looker Studio v1 | Nuevo embed actualizado |
| Modelo | `modelo_rendimiento_rf.pkl` | `componentes_semia_rf.pkl` |
| Dataset | `bolivar_agro_limpio.csv` | `dataset_eva_final.csv` (EVA completo) |
| Framework CSS | Bootstrap | Vanilla CSS + variables + glassmorphism |
| Animaciones | Ninguna | Scroll reveal, contadores, float, typing dots |
| Responsive | Parcial | Completamente responsive (mobile-first) |
| Tipografía | Default del browser | Google Fonts — Outfit |

---

## 🧪 Pruebas Realizadas

| Prueba | Resultado |
|---|---|
| Importación de todas las dependencias Python | ✅ OK |
| Carga del modelo desde archivo local | ✅ OK (~15 s) |
| Carga del dataset 351.920 filas | ✅ OK (~5 s) |
| `GET /api/municipios` — 1.061 municipios, 32 deptos | ✅ OK |
| `POST /api/recomendar` — CUMARIBO, 2026, Sem. A, 10 ha | ✅ PATILLA 11.58 t/ha |
| `POST /api/recomendar` — small talk "¿Quién eres?" | ✅ Respuesta conversacional |
| Dropdown Departamento → carga dinámica de municipios | ✅ OK |
| Menú hamburger en móvil | ✅ OK |
| Dashboard Looker Studio embebido | ✅ Visible |
| Contadores animados al hacer scroll | ✅ OK |
| Script `test_model.py` directo | ✅ Resultados correctos |

---

## ⏳ Pendientes del Proyecto

### 🔴 Prioritarios antes de publicar en producción

- [ ] **Crear `Dockerfile`** para contenedorizar la aplicación (Cloud Run / App Engine)
- [ ] **Agregar `gunicorn`** a `requirements.txt` — el servidor de desarrollo Werkzeug no es apto para producción
- [ ] **Ajustar `app.run()`** para leer el puerto desde variable de entorno `$PORT` (requerido por Cloud Run):
  ```python
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
  ```
- [ ] **Verificar que el objeto GCS sea público** para el fallback de descarga del modelo:
  ```bash
  gsutil acl ch -u AllUsers:R gs://unir-jbm/ML/componentes_semia_rf.pkl
  ```
- [ ] **Fijar versión de scikit-learn** a `==1.5.1` en `requirements.txt` para eliminar los `InconsistentVersionWarning` (o re-empaquetar el modelo con la versión instalada)

### 🟡 Mejoras recomendadas

- [ ] **Cachear el DataFrame en Redis o Memorystore** — los 351K registros (~200 MB en RAM) pueden ser un cuello de botella en Cloud Run con múltiples instancias
- [ ] **Tests unitarios** con `pytest` para `motor_recomendacion_semia()`, `find_municipio()` y los endpoints
- [ ] **Modo oscuro** — el CSS ya tiene todas las variables definidas; solo falta el toggle `<button>` y el bloque `@media (prefers-color-scheme: dark)`
- [ ] **Meta tags Open Graph** para compartir la página en redes sociales (`og:image`, `og:title`, `twitter:card`)
- [ ] **Manejo de errores mejorado en el frontend** — mostrar mensajes más descriptivos cuando el servidor tarda o falla

### 🟢 Funcionalidades futuras

- [ ] **Mapa interactivo de Colombia** — seleccionar el municipio haciendo clic en un mapa (Leaflet.js)
- [ ] **Comparador de municipios** — mostrar el Top 5 de dos municipios en paralelo
- [ ] **Exportar resultados** — botón para descargar la predicción como PDF o CSV
- [ ] **Historial de consultas** — guardar las últimas búsquedas en `localStorage`
- [ ] **API de información de cultivos** — endpoint `GET /api/cultivos/{nombre}` con descripción, época óptima de siembra y requerimientos de suelo

---

## 📊 Fuentes de Datos

| Fuente | Descripción | Enlace |
|---|---|---|
| MADR — EVA | Evaluaciones Agropecuarias Municipales 2007-2024 | [datos.gov.co](https://www.datos.gov.co/) |
| DANE | Validación geográfica de municipios | [dane.gov.co](https://www.dane.gov.co/) |
| Looker Studio | Dashboard interactivo de visualización | [Link del dashboard](https://datastudio.google.com/reporting/4519c930-4223-46cf-ad24-0104a0ccdf2a) |

---

## 📄 Licencia

Proyecto académico — Trabajo de Fin de Máster, UNIR 2025.
Los datos provienen de fuentes públicas del Gobierno de Colombia (MADR, DANE).

---

*Documentado con asistencia de IA (Google Gemini / Antigravity) · Julio 2025*

