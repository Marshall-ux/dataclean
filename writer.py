"""Generación del archivo Excel de salida con formato y múltiples pestañas."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple, Union

import pandas as pd

from config import EXCEL_SHEET_NAME_MAX

logger = logging.getLogger(__name__)


def escribir_excel(
    output_path: Union[str, Path],
    df_resumen: pd.DataFrame,
    hojas_procesadas: List[Tuple],
) -> None:
    """
    Escribe el archivo Excel final.

    hojas_procesadas: lista de tuplas
        (hoja_slug, df_original, df_limpio, df_indicadores, df_observaciones)
    """
    output_path = Path(output_path)

    with pd.ExcelWriter(str(output_path), engine="xlsxwriter") as writer:

        # Pestaña de índice general
        df_resumen.to_excel(writer, sheet_name="Resumen", index=False)
        ws_indice = writer.sheets["Resumen"]
        ws_indice.set_column(0, 5, 28)

        # Una iteración por hoja procesada
        for hoja_slug, df_orig, df_limp, df_ind, df_obs in hojas_procesadas:
            slug = str(hoja_slug)[:EXCEL_SHEET_NAME_MAX]

            # Construir nombres de pestaña seguros (máx. 31 chars en Excel)
            tags = {
                "orig": f"{slug}_Original",
                "limp": f"{slug}_Limpia",
                "kpi":  f"{slug}_Indicadores",
                "obs":  f"{slug}_Avisos",
            }

            df_orig.to_excel(writer, sheet_name=tags["orig"], index=False)
            df_limp.to_excel(writer, sheet_name=tags["limp"], index=False)
            df_ind.to_excel(writer, sheet_name=tags["kpi"], index=False)
            df_obs.to_excel(writer, sheet_name=tags["obs"], index=False)

            # Ancho de columnas
            for tag in ("orig", "limp"):
                writer.sheets[tags[tag]].set_column(0, 20, 18)
            for tag in ("kpi", "obs"):
                writer.sheets[tags[tag]].set_column(0, 5, 35)

    logger.info("Excel generado: %s", output_path.name)
