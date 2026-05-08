import pandas as pd
import numpy as np
import os
import glob
from procesador import procesar_planilla

# 1. Crear un DataFrame con basura en las primeras filas
data = [
    ["Reporte Confidencial - Uso Interno", np.nan, np.nan, np.nan],
    [np.nan, np.nan, np.nan, np.nan],
    ["Generado por:", "Sistema ERP", np.nan, "Fecha: 22/04/2026"],
    ["ID_Cliente", "Nombre_Completo", "Sucursal", "Monto_Deuda"], # Este es el verdadero header
    [101, "Juan Perez", "Centro", 15000.50],
    [102, "Maria Lopez", "Norte", 0],
    [103, "Carlos Diaz", "Centro ", 2300.00],  # Espacio extra para probar limpieza
    [104, "Ana Gimenez", "Sur", 500.00]
]

dirty_df = pd.DataFrame(data)
test_file = "test_dirty.xlsx"
dirty_df.to_excel(test_file, index=False, header=False)

print("Archivo sucio generado:")
print(dirty_df)
print("-" * 50)

# 2. Procesarlo con nuestra herramienta
try:
    print("Corriendo el procesador...")
    output_path = procesar_planilla(test_file, test_file)
    print(f"Éxito! Archivo generado en: {output_path}")
    
    # 3. Verificar el resultado leyendo la pestaña limpia
    # Limpiar el nombre original para obtener el tag de la pestaña
    xls = pd.ExcelFile(output_path)
    sheet_names = xls.sheet_names
    print("Pestañas generadas:", sheet_names)
    
    # Buscar la pestaña limpia (normalmente origin_Limpia, pero como la hoja se llama Sheet1 será Sheet1_Limpia)
    hoja_limpia = [s for s in sheet_names if s.endswith('_Limpia')][0]
    
    df_result = pd.read_excel(output_path, sheet_name=hoja_limpia)
    print("\n--- RESULTADO FINAL DETECTADO AUTOMÁTICAMENTE ---")
    print("Columnas detectadas:", df_result.columns.tolist())
    print(df_result)
    
except Exception as e:
    print(f"Error durante el procesamiento: {e}")

