import warnings; warnings.filterwarnings('ignore')
import joblib, pandas as pd, numpy as np

obj = joblib.load('../componentes_semia_rf.pkl')
rf_model    = obj['modelo']
rf_encoders = obj['encoders']
rf_scaler   = obj['scaler']
rf_cols     = obj['columnas_predictoras']

df = pd.read_csv('../dataset_eva_final.csv', low_memory=False)
df['Municipio']    = df['Municipio'].str.strip().str.upper()
df['Departamento'] = df['Departamento'].str.strip().str.upper()

municipio = 'CUMARIBO'
depto = df[df['Municipio']==municipio]['Departamento'].iloc[0]
cultivos_df = df[df['Municipio']==municipio][['Cultivo','Grupo_Cultivo','Ciclo_Cultivo']].drop_duplicates()

cols_cat = ['Departamento','Municipio','Grupo_Cultivo','Cultivo','Semestre','Ciclo_Cultivo']
cols_num = ['Anio','Area_Sembrada_ha']

rows = []
for _, row in cultivos_df.iterrows():
    rows.append({
        'Departamento': depto,
        'Municipio': municipio,
        'Grupo_Cultivo': row['Grupo_Cultivo'],
        'Cultivo': row['Cultivo'],
        'Anio': 2026,
        'Semestre': 'A',
        'Ciclo_Cultivo': row['Ciclo_Cultivo'],
        'Area_Sembrada_ha': 10.0
    })

X_pred = pd.DataFrame(rows, columns=rf_cols)
X_enc = X_pred.copy()

for col in cols_cat:
    le = rf_encoders.get(col)
    if le is None:
        continue
    known = set(le.classes_)
    X_enc[col] = X_enc[col].apply(lambda v: v if v in known else le.classes_[0])
    X_enc[col] = le.transform(X_enc[col].astype(str))

X_enc[cols_num] = rf_scaler.transform(X_enc[cols_num])
preds = rf_model.predict(X_enc[rf_cols])
X_pred['rend'] = preds
top5 = X_pred.sort_values('rend', ascending=False).head(5)
print("TOP 5 CUMARIBO 2026-A:")
for _, r in top5.iterrows():
    cultivo = r['Cultivo']
    rend = round(float(r['rend']), 2)
    print(f"  {cultivo:25s} {rend} t/ha")
print("OK - inferencia exitosa")
