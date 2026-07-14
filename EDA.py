import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. CARGA DE DATOS
# ==========================================
print("Cargando datasets...")
df_07_18 = pd.read_csv('eva_2007_2018.csv', sep=';', encoding='utf-8')
df_19_24 = pd.read_csv('eva_2019_2024.csv', sep=';', encoding='utf-8')

# ==========================================
# 2. HOMOLOGACIÓN DE COLUMNAS
# ==========================================
rename_07_18 = {
    'CÓD.DEP.': 'cod_dep', 'DEPARTAMENTO': 'departamento',
    'CÓD. MUN.': 'cod_mun', 'MUNICIPIO': 'municipio',
    'GRUPO DE CULTIVO': 'grupo_cultivo', 'SUBGRUPO DE CULTIVO': 'subgrupo_cultivo',
    'CULTIVO': 'cultivo', 'DESAGREGACIÓN REGIONAL Y/O SISTEMA PRODUCTIVO': 'desagregacion_cultivo',
    'AÑO': 'anio', 'PERIODO': 'periodo',
    'Área Sembrada (ha)': 'area_sembrada_ha', 'Área Cosechada (ha)': 'area_cosechada_ha',
    'Producción (t)': 'produccion_t', 'Rendimiento (t/ha)': 'rendimiento_t_ha',
    'ESTADO FISICO PRODUCCION': 'estado_fisico', 'NOMBRE CIENTIFICO': 'nombre_cientifico',
    'CICLO DE CULTIVO': 'ciclo_cultivo'
}

rename_19_24 = {
    'Código Dane departamento': 'cod_dep', 'Departamento': 'departamento',
    'Código Dane municipio': 'cod_mun', 'Municipio': 'municipio',
    'Desagregación cultivo': 'desagregacion_cultivo', 'Cultivo': 'cultivo',
    'Ciclo del cultivo': 'ciclo_cultivo', 'Grupo cultivo': 'grupo_cultivo',
    'Subgrupo': 'subgrupo_cultivo', 'Año': 'anio', 'Periodo': 'periodo',
    'Área sembrada (ha)': 'area_sembrada_ha', 'Área cosechada (ha)': 'area_cosechada_ha',
    'Producción (t)': 'produccion_t', 'Rendimiento (t/ha)': 'rendimiento_t_ha',
    'Nombre científico del cultivo': 'nombre_cientifico', 'Estado físico del cultivo': 'estado_fisico',
    'Código del cultivo': 'cod_cultivo'
}

df_07_18.rename(columns=rename_07_18, inplace=True)
df_19_24.rename(columns=rename_19_24, inplace=True)

# Concatenar
df = pd.concat([df_07_18, df_19_24], ignore_index=True)
df.drop('cod_cultivo', axis=1, inplace=True, errors='ignore') # Se elimina por falta de datos en histórico

# ==========================================
# 3. LIMPIEZA E IMPUTACIÓN DE DATOS
# ==========================================
print("Limpiando datos...")
# Estandarizar strings a mayúsculas sin espacios extremos
string_cols = ['departamento', 'municipio', 'grupo_cultivo', 'subgrupo_cultivo', 'cultivo', 'desagregacion_cultivo', 'estado_fisico', 'nombre_cientifico', 'ciclo_cultivo']
for col in string_cols:
    df[col] = df[col].astype(str).str.upper().str.strip()

# Formatear números (reemplazo de comas por puntos)
num_cols = ['area_sembrada_ha', 'area_cosechada_ha', 'produccion_t', 'rendimiento_t_ha']
for col in num_cols:
    if df[col].dtype == object:
        df[col] = df[col].astype(str).str.replace(',', '.').astype(float)

# Imputar rendimiento_t_ha calculándolo analíticamente
df['rendimiento_t_ha'] = np.where(df['area_cosechada_ha'] > 0, 
                                  df['produccion_t'] / df['area_cosechada_ha'], 
                                  0)

# ==========================================
# 4. EXPORTACIÓN PARA GCP Y DASHBOARDS
# ==========================================
output_file = 'dataset_eva_unificado_limpio.csv'
df.to_csv(output_file, index=False, sep=';', encoding='utf-8')
print(f"Dataset exportado exitosamente como {output_file}")

# ==========================================
# 5. ANÁLISIS EXPLORATORIO DE DATOS (EDA)
# ==========================================
print("Iniciando EDA...")

# 5.1 Información General
print(df.info())
print("\nEstadísticas Descriptivas:")
print(df.describe())

# 5.2 Matriz de Correlación
plt.figure(figsize=(8, 6))
correlation_matrix = df[['area_sembrada_ha', 'area_cosechada_ha', 'produccion_t', 'rendimiento_t_ha']].corr()
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt=".2f")
plt.title('Correlación de Variables Numéricas')
plt.show()

# 5.3 Top 10 Cultivos más sembrados históricamente
plt.figure(figsize=(10, 6))
top_cultivos = df.groupby('cultivo')['area_sembrada_ha'].sum().sort_values(ascending=False).head(10)
sns.barplot(x=top_cultivos.values, y=top_cultivos.index, palette='viridis')
plt.title('Top 10 Cultivos por Área Sembrada Histórica')
plt.xlabel('Área Sembrada Total (ha)')
plt.ylabel('Cultivo')
plt.show()

# 5.4 Evolución del área cosechada y producción a lo largo de los años
evolucion_anual = df.groupby('anio')[['area_cosechada_ha', 'produccion_t']].sum().reset_index()

fig, ax1 = plt.subplots(figsize=(12, 6))
ax1.set_xlabel('Año')
ax1.set_ylabel('Área Cosechada (ha)', color='tab:green')
ax1.plot(evolucion_anual['anio'], evolucion_anual['area_cosechada_ha'], color='tab:green', marker='o', label='Área Cosechada')
ax1.tick_params(axis='y', labelcolor='tab:green')

ax2 = ax1.twinx()
ax2.set_ylabel('Producción (t)', color='tab:blue')
ax2.plot(evolucion_anual['anio'], evolucion_anual['produccion_t'], color='tab:blue', marker='s', label='Producción')
ax2.tick_params(axis='y', labelcolor='tab:blue')

plt.title('Evolución Anual del Área Cosechada y Producción Agrícola (Colombia)')
plt.show()