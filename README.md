# DataClean — Asistente de Limpieza de Planillas

Herramienta web para limpiar, normalizar y analizar archivos Excel y CSV.  
Diseñada para personal administrativo: no requiere conocimientos técnicos.

---

## ¿Qué hace?

- Elimina filas vacías y filas repetidas
- Corrige mayúsculas, espacios extra y formatos de texto
- Unifica valores casi idénticos (ej: `"Kangoo"` y `"kangoo "`)
- Reconoce automáticamente columnas de fecha, correo electrónico, teléfono y moneda
- Detecta números fuera del rango habitual
- Genera un archivo Excel de salida con cinco pestañas explicadas

---

## Pestañas del Excel generado

| Pestaña | Contenido |
|---|---|
| **Resumen** | Estado general de cada hoja procesada: sin problemas, con avisos o con errores |
| **Hoja_Original** | Datos tal como estaban en el archivo original, sin modificar |
| **Hoja_Limpia** | Datos corregidos y normalizados listos para usar |
| **Hoja_Indicadores** | Análisis automático por columna: totales, promedios, categorías más frecuentes, registros por mes, etc. |
| **Hoja_Avisos** | Lista de correcciones aplicadas y puntos a revisar, ordenados por importancia (Urgente, Importante, A revisar, Informativo) |

---

## Requisitos

- Python 3.9 o superior
- pip

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/dataclean.git
cd dataclean

# 2. Crear entorno virtual (recomendado)
python -m venv venv
venv\Scripts\activate         # Windows
# source venv/bin/activate    # Mac / Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env        # Windows
# cp .env.example .env        # Mac / Linux
```

> Editá el archivo `.env` si necesitás cambiar el puerto u otras opciones.

---

## Cómo correr el servidor

```bash
python app.py
```

Abrí el navegador en **http://localhost:5001**

---

## Estructura del proyecto

```
dataclean/
├── app.py              # Servidor web (Flask): rutas y manejo de archivos
├── procesador.py       # Orquestador: coordina carga → limpieza → análisis → escritura
├── cleaner.py          # Motor de limpieza y normalización por columna
├── analyzer.py         # Motor de indicadores automáticos por columna
├── loader.py           # Carga de archivos y detección automática de encabezados
├── writer.py           # Generación del Excel de salida con múltiples pestañas
├── config.py           # Umbrales y constantes configurables
├── utils.py            # Configuración de logs
├── requirements.txt    # Dependencias Python
├── .env.example        # Plantilla de variables de entorno
├── static/
│   ├── css/styles.css  # Estilos de la interfaz
│   └── js/main.js      # Lógica del frontend (carga, drag & drop, estados)
└── templates/
    └── index.html      # Página principal
```

---

## Opciones de limpieza

Desde la interfaz web se pueden activar o desactivar individualmente:

| Opción | Descripción |
|---|---|
| Normalizar capitalización | Corrige mayúsculas y espacios extra en celdas de texto |
| Eliminar filas duplicadas | Remueve filas 100 % idénticas |
| Unificar variantes similares | Fusiona valores casi idénticos automáticamente |
| Detectar fechas automáticamente | Convierte columnas de texto con fechas al formato DD/MM/YYYY |
| Normalizar correos electrónicos | Pasa a minúsculas y detecta formatos inválidos |
| Detectar números fuera de lo normal | Reporta valores que se alejan mucho del rango habitual |

---

## Configuración avanzada

Las variables de entorno se configuran en el archivo `.env`:

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `SECRET_KEY` | Clave secreta de Flask | valor de desarrollo |
| `CORS_ORIGINS` | Orígenes permitidos para CORS | `*` |
| `FLASK_DEBUG` | Modo debug (solo desarrollo) | `false` |
| `PORT` | Puerto del servidor | `5001` |

Los umbrales internos de análisis (porcentaje de nulos para considerar urgente, umbral de similitud para unificar variantes, etc.) se ajustan directamente en `config.py`.

---

## Privacidad y seguridad

Los archivos subidos **no se almacenan**. El archivo original y el procesado se eliminan automáticamente del servidor en cuanto se completa la descarga.

---

## Dependencias principales

| Paquete | Uso |
|---|---|
| Flask | Servidor web |
| pandas | Procesamiento de datos |
| openpyxl / xlsxwriter | Lectura y escritura de Excel |
| rapidfuzz | Detección de variantes similares por similitud de texto |
| python-dotenv | Carga de variables de entorno desde `.env` |
