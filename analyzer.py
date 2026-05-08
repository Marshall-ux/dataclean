"""Motor Analítico: generación de indicadores de gestión (KPIs) por columna."""
from __future__ import annotations

import logging
from typing import Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


class MotorAnalitico:
    """
    Motor 2: Interpretación y Resumen Transversal.
    Genera KPIs semánticos por tipo de columna detectado.
    Completamente desacoplado del motor de limpieza.
    """

    def procesar(self, df: pd.DataFrame, metadata: Dict[str, str]) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["Tipo de Dato", "Columna", "Medición", "Resultado"])

        indicadores: List[Dict] = []
        cols_lower = {c: str(c).lower() for c in df.columns}

        for col_orig, c_low in cols_lower.items():
            tipo = metadata.get(col_orig, "otro")

            # ── FECHAS ───────────────────────────────────────────────────
            if tipo == "fecha" or any(x in c_low for x in ("fecha", "date", "registro", "creacion", "alta", "ingreso")):
                try:
                    fechas = pd.to_datetime(df[col_orig], errors="coerce").dropna()
                    if not fechas.empty:
                        meses = fechas.dt.to_period("M").value_counts().sort_index()
                        resultado = " | ".join(f"{k}: {v}" for k, v in meses.items())
                        indicadores.append({
                            "Tipo de Dato": "Fecha / Tiempo",
                            "Columna": col_orig,
                            "Medición": "Registros por mes",
                            "Resultado": resultado,
                        })
                except (ValueError, TypeError) as exc:
                    logger.warning("Error analizando fechas en '%s': %s", col_orig, exc)

            # ── ESTADOS / ETAPAS ─────────────────────────────────────────
            elif any(x in c_low for x in ("estado", "status", "etapa", "fase", "situacion", "condicion")):
                estados = df[col_orig].value_counts()
                resultado = " | ".join(f"{k} [{v}]" for k, v in estados.items())
                indicadores.append({
                    "Tipo de Dato": "Estado o Etapa",
                    "Columna": col_orig,
                    "Medición": "Cantidad por estado",
                    "Resultado": resultado,
                })

            # ── ESTRUCTURA ORGANIZATIVA ───────────────────────────────────
            elif any(x in c_low for x in ("area", "área", "sucursal", "sede", "departamento", "sector", "empresa", "oficina", "region", "región")):
                top = df[col_orig].value_counts().head(5)
                resultado = " | ".join(f"{k} [{v}]" for k, v in top.items())
                indicadores.append({
                    "Tipo de Dato": "Área / Sede / Departamento",
                    "Columna": col_orig,
                    "Medición": "Las 5 con más registros",
                    "Resultado": resultado,
                })

            # ── EMAILS ────────────────────────────────────────────────────
            elif tipo == "email":
                try:
                    dominios = df[col_orig].dropna().str.extract(r"@(.+)$")[0].value_counts().head(5)
                    resultado = " | ".join(f"{k} [{v}]" for k, v in dominios.items())
                    indicadores.append({
                        "Tipo de Dato": "Correo electrónico",
                        "Columna": col_orig,
                        "Medición": "Los 5 dominios de correo más usados",
                        "Resultado": resultado,
                    })
                except (ValueError, TypeError) as exc:
                    logger.warning("Error analizando emails en '%s': %s", col_orig, exc)

            # ── CATEGORÍAS ────────────────────────────────────────────────
            elif tipo == "categorica" or any(x in c_low for x in ("categoria", "categoría", "tipo", "rubro", "grupo", "genero", "marca", "modelo", "clase", "segmento")):
                top = df[col_orig].value_counts().head(5)
                resultado = " | ".join(f"{k} [{v}]" for k, v in top.items())
                indicadores.append({
                    "Tipo de Dato": "Categoría",
                    "Columna": col_orig,
                    "Medición": "Las 5 categorías más frecuentes",
                    "Resultado": resultado,
                })

            # ── NUMÉRICO ─────────────────────────────────────────────────
            elif tipo == "numerico":
                try:
                    col_num = pd.to_numeric(df[col_orig], errors="coerce")
                    suma = col_num.sum()
                    promedio = col_num.mean()
                    maximo = col_num.max()
                    minimo = col_num.min()
                    if pd.isna(suma) or pd.isna(promedio):
                        continue

                    if any(x in c_low for x in ("monto", "importe", "total", "precio", "costo", "valor", "saldo", "factura")):
                        indicadores.append({
                            "Tipo de Dato": "Monto / Dinero",
                            "Columna": col_orig,
                            "Medición": "Suma, promedio, mínimo y máximo",
                            "Resultado": (
                                f"Suma: {suma:,.2f} | Promedio: {promedio:,.2f} | "
                                f"Mín: {minimo:,.2f} | Máx: {maximo:,.2f}"
                            ),
                        })
                    elif any(x in c_low for x in ("cantidad", "qty", "stock", "unidades", "items", "piezas")):
                        indicadores.append({
                            "Tipo de Dato": "Cantidad",
                            "Columna": col_orig,
                            "Medición": "Total y promedio de unidades",
                            "Resultado": f"Total: {suma:,.0f} uds. | Promedio: {promedio:,.1f}",
                        })
                    else:
                        indicadores.append({
                            "Tipo de Dato": "Número",
                            "Columna": col_orig,
                            "Medición": "Promedio, mínimo y máximo",
                            "Resultado": (
                                f"Promedio: {promedio:.2f} | Mín: {minimo:.2f} | Máx: {maximo:.2f}"
                            ),
                        })
                except (TypeError, ValueError) as exc:
                    logger.warning("Error calculando KPI numérico para '%s': %s", col_orig, exc)

        # Fila de resumen general siempre al tope
        indicadores.insert(0, {
            "Tipo de Dato": "Resumen general",
            "Columna": "Todas",
            "Medición": "Tamaño de la tabla",
            "Resultado": f"{len(df)} registros × {len(df.columns)} columnas.",
        })

        return pd.DataFrame(indicadores)
