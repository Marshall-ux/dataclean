import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

folder = r'c:\Users\Marlen Virga\Desktop\Pagina\limpiador_planillas'
sys.path.append(folder)
from procesador import procesar_planilla

files = [f for f in os.listdir(folder) if f.endswith('.xlsx') and not f.startswith('Procesado_') and f.startswith('42')]

for file in files:
    full_path = os.path.join(folder, file)
    print(f'\nProcesando archivo: {file}')
    try:
        res = procesar_planilla(full_path, file)
        print(f'✅ Éxito! Guardado en: {res}')
    except Exception as e:
        print(f'❌ Error: {e}')
