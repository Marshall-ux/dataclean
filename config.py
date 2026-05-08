"""Configuración centralizada de umbrales y constantes del proyecto."""
from pathlib import Path

BASE_DIR = Path(__file__).parent

# ── Fuzzy matching ────────────────────────────────────────────────────────────
FUZZY_MAX_UNIQUE_VALUES: int = 250      # Columnas con más únicos quedan excluidas del matching
FUZZY_AUTO_MERGE_THRESHOLD: float = 0.92  # Por encima de este score → unificación automática
FUZZY_SUGGEST_THRESHOLD: float = 0.82    # Por encima de este score → sugerencia de revisión

# ── Clasificación de columnas ────────────────────────────────────────────────
CATEGORICAL_MAX_UNIQUE: int = 50    # Columnas con ≤ este número de únicos → "categorica"

# ── Umbrales de nulos ────────────────────────────────────────────────────────
NULL_CRITICAL_RATIO: float = 0.50   # > 50 % nulos → Crítica
NULL_HIGH_RATIO: float = 0.20       # > 20 % nulos → Alta

# ── Detección de encabezados ─────────────────────────────────────────────────
MAX_HEADER_SEARCH_ROWS: int = 20    # Cuántas filas escanear para buscar el header real

# ── Rutas ────────────────────────────────────────────────────────────────────
UPLOAD_FOLDER: Path = BASE_DIR / "uploads"
MAX_FILE_SIZE_MB: int = 16

# ── Detección automática ─────────────────────────────────────────────────────
EMAIL_DETECTION_RATIO: float = 0.30   # Si ≥ 30 % de valores contienen '@' → columna email
DATE_DETECTION_RATIO: float = 0.60    # Si ≥ 60 % de valores parsean como fecha → convertir
CURRENCY_DETECTION_RATIO: float = 0.40  # Si ≥ 40 % tienen símbolo de moneda → convertir

# ── Outliers ─────────────────────────────────────────────────────────────────
OUTLIER_IQR_MULTIPLIER: float = 1.5

# ── Excel de salida ──────────────────────────────────────────────────────────
# Excel permite hasta 31 chars; el sufijo más largo es "_Indicadores" (12 chars) → 31-12=19
EXCEL_SHEET_NAME_MAX: int = 19
