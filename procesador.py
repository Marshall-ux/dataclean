"""
Orquestador principal del pipeline de limpieza.
Coordina: carga → detección de header → limpieza → análisis → escritura.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from werkzeug.utils import secure_filename

from analyzer import MotorAnalitico
from cleaner import MotorLimpieza
from config import EXCEL_SHEET_NAME_MAX
from loader import auto_detect_header, cargar_archivo
from writer import escribir_excel

logger = logging.getLogger(__name__)


def procesar_planilla(
    filepath: str,
    original_filename: str,
    opciones: Optional[Dict] = None,
) -> str:
    """
    Procesa un archivo Excel o CSV y genera un Excel limpio con KPIs y observaciones.

    Args:
        filepath: Ruta absoluta del archivo subido.
        original_filename: Nombre original del archivo (para nombrar el output).
        opciones: Diccionario de opciones de limpieza seleccionadas por el usuario.

    Returns:
        Ruta absoluta del archivo Excel de salida.
    """
    filepath = Path(filepath)
    output_dir = filepath.parent

    # Nombre de salida seguro con timestamp
    safe_stem = secure_filename(original_filename.rsplit(".", 1)[0])
    timestamp = datetime.now().strftime("%d%m%y_%H%M")
    output_filename = f"Procesado_{safe_stem}_{timestamp}.xlsx"
    output_path = output_dir / output_filename

    # ── Carga ────────────────────────────────────────────────────────────────
    try:
        hojas_dict = cargar_archivo(str(filepath))
    except Exception as exc:
        raise RuntimeError(f"Error al cargar el archivo: {exc}") from exc

    if not hojas_dict:
        raise ValueError("El archivo está vacío o no contiene hojas legibles.")

    resumen_general: List[Dict] = []
    hojas_procesadas: List = []

    # ── Procesamiento hoja por hoja ──────────────────────────────────────────
    for nombre_hoja, df in hojas_dict.items():
        logger.info("Procesando hoja '%s' (%d filas × %d cols).",
                    nombre_hoja, len(df), len(df.columns))

        if df.empty or len(df.columns) == 0:
            resumen_general.append({
                "Hoja de Origen": nombre_hoja,
                "Estado": "Sin datos",
                "Motivo": "La hoja no contiene datos.",
            })
            continue

        df = auto_detect_header(df)

        if df.empty or len(df.columns) == 0:
            resumen_general.append({
                "Hoja de Origen": nombre_hoja,
                "Estado": "Sin datos",
                "Motivo": "No se encontraron datos luego de detectar el encabezado.",
            })
            continue

        try:
            limpiador = MotorLimpieza(opciones=opciones)
            analitico = MotorAnalitico()

            df_limpio, df_obs, metadata = limpiador.procesar(df)
            df_indicadores = analitico.procesar(df_limpio, metadata)

            alertas = len(df_obs[df_obs["Importancia"].isin(["Urgente", "Importante"])])
            estado = f"Con avisos ({alertas} avisos)" if alertas > 0 else "Sin problemas"
            resumen_general.append({
                "Hoja de Origen": nombre_hoja,
                "Estado": estado,
                "Filas Procesadas": len(df_limpio),
                "Columnas": len(df_limpio.columns),
            })

            hoja_slug = str(nombre_hoja)[:EXCEL_SHEET_NAME_MAX]
            hojas_procesadas.append((hoja_slug, df, df_limpio, df_indicadores, df_obs))

        except Exception as exc:
            logger.error("Error procesando hoja '%s': %s", nombre_hoja, exc, exc_info=True)
            resumen_general.append({
                "Hoja de Origen": nombre_hoja,
                "Estado": "Error al procesar",
                "Motivo": str(exc),
            })

    df_resumen = pd.DataFrame(resumen_general)

    # ── Escritura del Excel de salida ────────────────────────────────────────
    escribir_excel(output_path, df_resumen, hojas_procesadas)

    return str(output_path)
