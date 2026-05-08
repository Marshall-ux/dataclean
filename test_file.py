import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

folder = r'c:\Users\Marlen Virga\Desktop\Pagina\limpiador_planillas'
files = os.listdir(folder)
target = next((f for f in files if "En este caso" in f), None)

if target:
    old_path = os.path.join(folder, target)
    new_path = os.path.join(folder, "test_data.xlsx")
    
    extended_path = "\\\\?\\" + os.path.abspath(old_path)
    extended_new = "\\\\?\\" + os.path.abspath(new_path)
    
    try:
        os.rename(extended_path, extended_new)
        print("Renamed to test_data.xlsx")
    except Exception as e:
        print("Rename failed:", e)
else:
    print("Target file not found dynamically. Proceeding to processing.")

sys.path.append(folder)
from procesador import procesar_planilla

print('Iniciando procesamiento del archivo: test_data.xlsx')
try:
    res = procesar_planilla(os.path.join(folder, "test_data.xlsx"), "test_data.xlsx")
    print('Terminado! Output guardado en:', res)
except Exception as e:
    print('Error:', e)
    raise e
