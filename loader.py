"""Carga de archivos y detección automática de encabezados."""
from __future__ import annotations

import logging
from typing import Dict

import pandas as pd

from config import MAX_HEADER_SEARCH_ROWS

logger = logging.getLogger(__name__)

# Encodings a probar en orden para archivos CSV
_CSV_ENCODINGS = ("utf-8-sig", "utf-8", "latin-1", "cp1252")

# Mapa de extensión → engine de pandas
# xlrd 2.x solo soporta .xls (Excel 97-2003)
# openpyxl soporta .xlsx y .xlsm
# pyxlsb soporta .xlsb (Excel Binary)
_ENGINE_MAP = {
    ".xls":  "xlrd",
    ".xlsx": "openpyxl",
    ".xlsm": "openpyxl",
    ".xlsb": "pyxlsb",
}


def cargar_archivo(filepath: str) -> Dict[str, pd.DataFrame]:
    """
    Lee un archivo CSV o Excel y retorna un diccionario {nombre_hoja: DataFrame}.
    Soporta: .csv, .xlsx, .xls (Excel 97-2003), .xlsm, .xlsb.
    Los DataFrames se cargan sin encabezado (header=None) para que
    auto_detect_header pueda encontrar la fila real de columnas.
    """
    fp = filepath.lower()

    if fp.endswith(".csv"):
        df = _leer_csv(filepath)
        return {"DatosCSV": df}

    return _leer_excel(filepath)


def _leer_excel(filepath: str) -> Dict[str, pd.DataFrame]:
    """
    Lee cualquier formato Excel detectando el engine correcto por extensión.
    Provee mensajes de error claros para problemas comunes.
    """
    ext = "." + filepath.rsplit(".", 1)[-1].lower()
    engine = _ENGINE_MAP.get(ext)

    if engine is None:
        raise ValueError(
            f"Formato '{ext}' no soportado. "
            "Formatos válidos: .xlsx, .xls (Excel 97-2003), .xlsm, .xlsb, .csv"
        )

    logger.info("Cargando archivo Excel (engine: %s)…", engine)

    try:
        hojas = pd.read_excel(filepath, sheet_name=None, header=None, engine=engine)
    except Exception as exc:
        msg = str(exc).lower()
        # Mensajes de error más amigables para casos comunes
        if "password" in msg or "encrypted" in msg or "workbook is encrypted" in msg:
            raise RuntimeError(
                "El archivo está protegido con contraseña. "
                "Quitá la protección antes de subir el archivo."
            ) from exc
        if "no such file" in msg:
            raise RuntimeError("El archivo no se encontró en el servidor.") from exc
        if "xlrd" in msg and "install" in msg:
            raise RuntimeError(
                "Falta la librería para leer archivos .xls. "
                "Ejecutá: pip install xlrd"
            ) from exc
        if "openpyxl" in msg:
            raise RuntimeError(
                "Error al leer el archivo .xlsx. "
                "El archivo puede estar dañado o ser de una versión no soportada."
            ) from exc
        raise RuntimeError(f"No se pudo abrir el archivo Excel: {exc}") from exc

    if not hojas:
        raise ValueError("El archivo Excel no contiene hojas con datos.")

    # Filtrar hojas completamente vacías (evita procesar hojas de gráficos, etc.)
    hojas_con_datos = {
        nombre: df for nombre, df in hojas.items()
        if df is not None and not df.empty
    }

    if not hojas_con_datos:
        raise ValueError(
            "El archivo Excel no contiene hojas con datos. "
            "Verificá que no sea solo un libro de gráficos."
        )

    logger.info(
        "Archivo cargado: %d hoja(s) con datos (%s).",
        len(hojas_con_datos),
        ", ".join(f"'{n}'" for n in hojas_con_datos),
    )
    return hojas_con_datos


def _leer_csv(filepath: str) -> pd.DataFrame:
    """Intenta leer el CSV con varios encodings para cubrir archivos con tildes/ñ."""
    for enc in _CSV_ENCODINGS:
        try:
            df = pd.read_csv(filepath, header=None, encoding=enc, encoding_errors="replace")
            logger.info("CSV leído con encoding '%s'.", enc)
            return df
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as exc:
            raise RuntimeError(f"Error al leer el CSV: {exc}") from exc
    raise ValueError("No se pudo determinar el encoding del archivo CSV.")


def auto_detect_header(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta la fila real de encabezados buscando la mayor densidad de strings
    únicos en las primeras MAX_HEADER_SEARCH_ROWS filas.
    Descarta todas las filas anteriores ('basura' de exportadores de CRM).
    """
    if df.empty or len(df.columns) == 0:
        return df

    best_row_idx = 0
    best_score = -1

    for i in range(min(MAX_HEADER_SEARCH_ROWS, len(df))):
        row = df.iloc[i]
        # Contamos valores de texto no vacíos y no "nan"
        strings = [
            str(v).strip()
            for v in row.dropna()
            if str(v).strip() not in ("", "nan")
        ]
        if len(strings) > best_score:
            best_score = len(strings)
            best_row_idx = i

    if best_score == 0:
        return df

    new_cols = _unique_column_names(df.iloc[best_row_idx])
    df = df.iloc[best_row_idx + 1:].reset_index(drop=True)
    df.columns = new_cols
    return df


def _unique_column_names(header_row: pd.Series) -> list:
    """
    Genera una lista de nombres de columna únicos a partir de la fila de encabezado.
    Los duplicados reciben un sufijo numérico incremental.
    """
    used: set = set()
    cols = []

    for j, val in enumerate(header_row):
        name = str(val).strip() if pd.notna(val) and str(val).strip() not in ("", "nan") else f"Columna_{j}"
        base = name
        counter = 1
        while name in used:
            name = f"{base}_{counter}"
            counter += 1
        used.add(name)
        cols.append(name)

    return cols
