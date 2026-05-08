"""Motor de Limpieza: normalización, validación y observaciones por columna."""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from rapidfuzz import fuzz as _fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False

from config import (
    CATEGORICAL_MAX_UNIQUE,
    CURRENCY_DETECTION_RATIO,
    DATE_DETECTION_RATIO,
    EMAIL_DETECTION_RATIO,
    FUZZY_AUTO_MERGE_THRESHOLD,
    FUZZY_MAX_UNIQUE_VALUES,
    FUZZY_SUGGEST_THRESHOLD,
    NULL_CRITICAL_RATIO,
    NULL_HIGH_RATIO,
    OUTLIER_IQR_MULTIPLIER,
)

logger = logging.getLogger(__name__)

# Cadenas de texto que representan "vacío" después de aplicar title()
_NULL_TEXT_INDICATORS = frozenset({
    "", "Nan", "None", "N/A", "Na", "#N/A", "Null", "Nd",
    "S/D", "S/N", "-", "--", "Sin Dato", "Sin Informacion",
    "No Aplica", "N/D",
})

# Keywords para detectar columnas de teléfono por nombre
_PHONE_KEYWORDS = ("tel", "cel", "phone", "movil", "móvil", "fono", "celular", "telefono", "whatsapp")


class MotorLimpieza:
    """
    Motor 1: Orden y Preparación.
    Limpia, normaliza y cataloga cada columna emitiendo observaciones
    categorizadas por severidad.
    """

    def __init__(self, opciones: Optional[Dict] = None) -> None:
        self.observaciones: List[Dict] = []
        self.metadata: Dict[str, str] = {}
        # Opciones con defaults activados — se sobreescriben con lo que viene del frontend
        self.opciones: Dict = {
            "normalizar_texto": True,
            "unificar_variantes": True,
            "eliminar_duplicados": True,
            "detectar_fechas": True,
            "normalizar_emails": True,
            "detectar_outliers": True,
            **(opciones or {}),
        }

    # ── Logging ──────────────────────────────────────────────────────────────

    def log(self, col: str, severidad: str, tipo: str, detalle: str) -> None:
        self.observaciones.append({
            "Importancia": severidad,
            "Columna": col,
            "Tipo de Aviso": tipo,
            "Detalle": detalle,
        })

    # ── Detectores de tipo de columna ────────────────────────────────────────

    def _es_email(self, series: pd.Series) -> bool:
        """Retorna True si ≥ EMAIL_DETECTION_RATIO de los valores no-nulos contienen '@'."""
        no_nulos = series.dropna().astype(str)
        if no_nulos.empty:
            return False
        return (no_nulos.str.contains("@", regex=False).sum() / len(no_nulos)) >= EMAIL_DETECTION_RATIO

    def _es_telefono(self, col_name: str) -> bool:
        """Detecta columnas de teléfono/celular por nombre."""
        return any(k in col_name.lower() for k in _PHONE_KEYWORDS)

    # ── Transformadores ──────────────────────────────────────────────────────

    def _normalizar_email(self, series: pd.Series) -> pd.Series:
        """Convierte emails a minúsculas eliminando espacios laterales."""
        s = series.astype(str).str.strip().str.lower()
        return s.where(series.notna(), np.nan)

    def _normalizar_telefono(self, series: pd.Series) -> pd.Series:
        """Elimina caracteres no numéricos preservando el '+' inicial internacional."""
        def _clean(val: object) -> object:
            if pd.isna(val):
                return val
            s = str(val).strip()
            tiene_plus = s.startswith("+")
            digits = re.sub(r"\D", "", s)
            if not digits:
                return val
            return ("+" + digits) if tiene_plus else digits

        return series.map(_clean)

    def _limpiar_texto(self, series: pd.Series) -> pd.Series:
        """
        Normaliza texto: strip, colapsa espacios internos, aplica title-case
        y convierte representaciones de nulo ("N/A", "Null", "-", etc.) a NaN real.
        IMPORTANTE: no se aplica a emails ni teléfonos (tienen su propio normalizador).
        """
        s = series.fillna("").astype(str)
        s = s.str.strip()
        s = s.str.replace(r"\s+", " ", regex=True)
        s = s.str.title()
        # Convertir texto-nulo a NaN real
        s = s.replace(dict.fromkeys(_NULL_TEXT_INDICATORS, np.nan))
        # Restaurar NaN donde el original era NaN
        return s.where(series.notna(), np.nan)

    def _detectar_fechas(self, series: pd.Series) -> Optional[pd.Series]:
        """
        Intenta parsear la serie como fechas (formato DD/MM/YYYY prioritario).
        Retorna la serie convertida si ≥ DATE_DETECTION_RATIO de valores parsean,
        o None si no se detecta como columna de fechas.
        """
        no_nulos = series.dropna()
        if no_nulos.empty:
            return None
        # format='mixed' (pandas ≥ 2.0) evita el UserWarning; fallback para versiones anteriores
        try:
            parsed = pd.to_datetime(no_nulos, errors="coerce", format="mixed", dayfirst=True)
        except TypeError:
            parsed = pd.to_datetime(no_nulos, errors="coerce", dayfirst=True)
        if parsed.notna().sum() / len(no_nulos) >= DATE_DETECTION_RATIO:
            try:
                return pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=True)
            except TypeError:
                return pd.to_datetime(series, errors="coerce", dayfirst=True)
        return None

    def _normalizar_moneda(self, series: pd.Series) -> Optional[pd.Series]:
        """
        Detecta columnas con valores monetarios (ej: "$1.500,00") y los convierte
        a float estándar. Solo actúa si ≥ CURRENCY_DETECTION_RATIO tienen símbolo.
        """
        no_nulos = series.dropna().astype(str)
        if no_nulos.empty:
            return None

        ratio = no_nulos.str.contains(r"[$€£¥]", regex=True).sum() / len(no_nulos)
        if ratio < CURRENCY_DETECTION_RATIO:
            return None

        def _parse(val: object) -> float:
            if pd.isna(val):
                return np.nan
            s = re.sub(r"[$€£¥\s]", "", str(val).strip())
            # Formato argentino: 1.000,50 → 1000.50
            if re.search(r"\d{1,3}(\.\d{3})+,\d{2}$", s):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
            try:
                return float(s)
            except ValueError:
                return np.nan

        result = series.map(_parse)
        # Verificar que la conversión tuvo éxito mínimo
        if result.notna().sum() < 0.30 * series.notna().sum():
            return None
        return result

    # ── Fuzzy matching ───────────────────────────────────────────────────────

    def _fuzzy_match(self, counts: pd.Series) -> Tuple[Dict, Dict]:
        """
        Unificación borrosa de variantes similares.
        Usa rapidfuzz si está disponible (10–100× más rápido que difflib).
        Los valores más frecuentes (primeros en counts) son los "canónicos":
        las variantes raras se fusionan hacia el valor más frecuente.
        """
        unique_vals = counts.index.tolist()
        if len(unique_vals) <= 1 or len(unique_vals) > FUZZY_MAX_UNIQUE_VALUES:
            return {}, {}

        reemplazos: Dict[str, str] = {}
        sugerencias: Dict[str, str] = {}

        for i, v1 in enumerate(unique_vals):
            if v1 in reemplazos:
                continue
            for v2 in unique_vals[i + 1:]:
                if v2 in reemplazos:
                    continue
                if _HAS_RAPIDFUZZ:
                    score = _fuzz.ratio(str(v1), str(v2)) / 100.0
                else:
                    import difflib
                    score = difflib.SequenceMatcher(None, str(v1), str(v2)).ratio()

                if score > FUZZY_AUTO_MERGE_THRESHOLD:
                    reemplazos[v2] = v1
                elif score > FUZZY_SUGGEST_THRESHOLD:
                    sugerencias[v2] = v1

        return reemplazos, sugerencias

    # ── Outliers ─────────────────────────────────────────────────────────────

    def _detectar_outliers(self, series: pd.Series, col: str) -> None:
        """Detecta valores atípicos usando el método IQR y los reporta."""
        nums = pd.to_numeric(series, errors="coerce").dropna()
        if len(nums) < 10:
            return
        q1, q3 = nums.quantile(0.25), nums.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return
        lo = q1 - OUTLIER_IQR_MULTIPLIER * iqr
        hi = q3 + OUTLIER_IQR_MULTIPLIER * iqr
        outliers = nums[(nums < lo) | (nums > hi)]
        if not outliers.empty:
            ejemplos = ", ".join(str(round(x, 2)) for x in outliers.head(3))
            self.log(
                col, "A revisar", "Números fuera de lo normal",
                f"{len(outliers)} números muy alejados del valor habitual [{lo:.2f} – {hi:.2f}]. "
                f"Conviene verificarlos: {ejemplos}",
            )

    # ── Orquestador principal ────────────────────────────────────────────────

    def procesar(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
        """
        Procesa el DataFrame aplicando todas las transformaciones de limpieza
        según las opciones configuradas.
        Retorna: (df_limpio, df_observaciones, metadata_de_columnas)
        """
        df_limpio = df.copy()

        # 1. Eliminar filas 100 % vacías
        antes = len(df_limpio)
        df_limpio.dropna(how="all", inplace=True)
        df_limpio.reset_index(drop=True, inplace=True)
        eliminadas = antes - len(df_limpio)
        if eliminadas > 0:
            self.log("Múltiples", "Informativo", "Filas en blanco eliminadas",
                     f"Se eliminaron {eliminadas} filas completamente vacías.")

        # 2. Eliminar duplicados exactos
        if self.opciones.get("eliminar_duplicados", True):
            antes = len(df_limpio)
            df_limpio.drop_duplicates(inplace=True)
            df_limpio.reset_index(drop=True, inplace=True)
            duplicadas = antes - len(df_limpio)
            if duplicadas > 0:
                self.log("Múltiples", "Importante", "Filas repetidas eliminadas",
                         f"Se eliminaron {duplicadas} filas idénticas exactas.")

        # Normalizar StringDtype (pandas 2.x) a object para que todo el pipeline
        # funcione igual que con pandas 1.x
        for col in df_limpio.columns:
            if pd.api.types.is_string_dtype(df_limpio[col]) and df_limpio[col].dtype != object:
                df_limpio[col] = df_limpio[col].astype(object)

        total = len(df_limpio)

        for col in df_limpio.columns:
            serie = df_limpio[col]
            nulos = int(serie.isna().sum())
            no_nulos_count = total - nulos

            # ── Análisis de nulos ─────────────────────────────────────────
            if nulos > 0 and total > 0:
                rc = nulos / total
                sev = "Urgente" if rc > NULL_CRITICAL_RATIO else ("Importante" if rc > NULL_HIGH_RATIO else "A revisar")
                self.log(col, sev, "Celdas vacías",
                         f"{nulos} celdas sin dato ({int(rc * 100)} % del total).")

            # ── Columna constante ─────────────────────────────────────────
            if no_nulos_count > 0 and serie.dropna().nunique() == 1:
                self.log(col, "Informativo", "Columna con un solo valor",
                         f'Todos los registros tienen el valor "{serie.dropna().iloc[0]}". '
                         "Es posible que esta columna no agregue información útil.")

            # ── Columnas de texto (dtype object) ──────────────────────────
            if serie.dtype == object:

                # ¿Todos los valores no-nulos son numéricos?
                try_num = pd.to_numeric(serie, errors="coerce")
                num_ok = int(try_num.notna().sum())

                if num_ok > 0 and num_ok == no_nulos_count:
                    df_limpio[col] = try_num
                    self.metadata[col] = "numerico"
                    if self.opciones.get("detectar_outliers", True):
                        self._detectar_outliers(df_limpio[col], col)
                    continue

                if num_ok > 0:
                    self.log(col, "Importante", "Mezcla de números y texto",
                             f"{num_ok} celdas tienen números mezclados con texto. Puede generar errores al calcular.")

                # ¿Moneda?
                moneda = self._normalizar_moneda(serie)
                if moneda is not None:
                    df_limpio[col] = moneda
                    self.metadata[col] = "numerico"
                    self.log(col, "Informativo", "Montos corregidos a número",
                             f"{int(moneda.notna().sum())} valores de dinero convertidos a número para poder operar con ellos.")
                    if self.opciones.get("detectar_outliers", True):
                        self._detectar_outliers(df_limpio[col], col)
                    continue

                # ¿Email?
                if self.opciones.get("normalizar_emails", True) and self._es_email(serie):
                    s_clean = self._normalizar_email(serie)
                    cambios = (serie.fillna("") != s_clean.fillna("")).sum()
                    if cambios > 0:
                        self.log(col, "Informativo", "Correos corregidos",
                                 f"{cambios} correos electrónicos convertidos a minúsculas para unificar el formato.")
                    # Validar formato
                    invalidos = s_clean.dropna()
                    invalidos = invalidos[~invalidos.str.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
                    if not invalidos.empty:
                        self.log(col, "A revisar", "Correos con formato incorrecto",
                                 f"{len(invalidos)} correos tienen un formato inválido (les falta el '@' o el dominio). "
                                 f"Ej.: {', '.join(invalidos.head(3).tolist())}")
                    df_limpio[col] = s_clean
                    self.metadata[col] = "email"
                    continue

                # ¿Teléfono?
                if self._es_telefono(col):
                    s_clean = self._normalizar_telefono(serie)
                    cambios = (serie.fillna("") != s_clean.fillna("")).sum()
                    if cambios > 0:
                        self.log(col, "Informativo", "Teléfonos corregidos",
                                 f"{cambios} teléfonos corregidos: se eliminaron guiones, paréntesis y espacios para dejar solo los números.")
                    df_limpio[col] = s_clean
                    self.metadata[col] = "telefono"
                    continue

                # ¿Fecha?
                if self.opciones.get("detectar_fechas", True):
                    fecha_serie = self._detectar_fechas(serie)
                    if fecha_serie is not None:
                        df_limpio[col] = fecha_serie
                        self.metadata[col] = "fecha"
                        self.log(col, "Informativo", "Fechas reconocidas automáticamente",
                                 "Los valores de esta columna fueron reconocidos como fechas y organizados en formato DD/MM/YYYY.")
                        continue

                # ── Limpieza general de texto ─────────────────────────────
                if self.opciones.get("normalizar_texto", True):
                    s_clean = self._limpiar_texto(serie)
                    sentinel = "__DATACLEAM_NULL__"
                    mask_cambio = (
                        serie.fillna(sentinel).astype(str) != s_clean.fillna(sentinel).astype(str)
                    ) & serie.notna()
                    cambios_total = int(mask_cambio.sum())

                    if cambios_total > 0:
                        nuevos_nulos = int((serie.notna() & s_clean.isna()).sum())
                        if nuevos_nulos > 0:
                            self.log(col, "Informativo", "Celdas con texto vacío corregidas",
                                     f"{nuevos_nulos} celdas que decían 'N/A', 'Null', '-', etc. "
                                     "fueron convertidas a celdas realmente vacías.")
                        resto = cambios_total - nuevos_nulos
                        if resto > 0:
                            self.log(col, "Informativo", "Texto corregido",
                                     f"{resto} celdas corregidas: se eliminaron espacios sobrantes y se estandarizó el uso de mayúsculas.")
                    df_limpio[col] = s_clean

                # ── Fuzzy matching ────────────────────────────────────────
                if self.opciones.get("unificar_variantes", True):
                    counts = df_limpio[col].value_counts()
                    reemplazos, sugerencias = self._fuzzy_match(counts)

                    if reemplazos:
                        afect = int(df_limpio[col].isin(reemplazos).sum())
                        df_limpio[col] = df_limpio[col].replace(reemplazos)
                        self.log(col, "A revisar", "Valores similares unificados",
                                 f"{len(reemplazos)} valores casi idénticos fueron unificados automáticamente "
                                 f"({afect} celdas afectadas). Revisá que los cambios sean correctos.")
                    if sugerencias:
                        ejemplo = next(iter(sugerencias.items()))
                        self.log(col, "A revisar", "Valores parecidos para revisar",
                                 f"{len(sugerencias)} valores muy parecidos que podrían ser el mismo. Revisalos antes de usar esta columna. "
                                 f'Ej.: "{ejemplo[0]}" y "{ejemplo[1]}"')

                    unicos = int(df_limpio[col].nunique(dropna=True))
                else:
                    unicos = int(df_limpio[col].nunique(dropna=True))

                self.metadata[col] = "categorica" if 0 < unicos <= CATEGORICAL_MAX_UNIQUE else "texto"

            # ── Columnas numéricas ────────────────────────────────────────
            elif pd.api.types.is_numeric_dtype(serie):
                self.metadata[col] = "numerico"
                if self.opciones.get("detectar_outliers", True):
                    self._detectar_outliers(serie, col)

            # ── Columnas de fecha ─────────────────────────────────────────
            elif pd.api.types.is_datetime64_any_dtype(serie):
                self.metadata[col] = "fecha"

        if not self.observaciones:
            self.log("-", "Informativo", "Todo en orden",
                     "La tabla no presenta problemas. No fue necesario realizar correcciones.")

        return df_limpio, pd.DataFrame(self.observaciones), self.metadata
