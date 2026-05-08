"""Aplicación Flask: rutas, manejo de uploads y descarga del archivo procesado."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from flask import Flask, after_this_request, jsonify, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

# Cargar variables de entorno desde .env si python-dotenv está instalado
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask_cors import CORS

from procesador import procesar_planilla
from utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ── Seguridad ─────────────────────────────────────────────────────────────────
app.secret_key = os.environ.get("SECRET_KEY", "dev-insecure-key-cambiame-en-produccion")

# CORS: restringir a orígenes permitidos (configurar CORS_ORIGINS en .env en producción)
_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]
CORS(app, origins=_cors_origins)

# ── Configuración de archivos ─────────────────────────────────────────────────
UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "xlsm", "xlsb"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Rutas ─────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Validar presencia del archivo
        if "file" not in request.files:
            return jsonify({"error": "No se encontró el archivo en la petición."}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "No se seleccionó ningún archivo."}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Formato no permitido. Subí un archivo Excel (.xlsx, .xls) o CSV."}), 400

        # Parsear opciones de limpieza enviadas desde el frontend
        opciones_raw = request.form.get("opciones", "{}")
        try:
            opciones = json.loads(opciones_raw)
        except (json.JSONDecodeError, ValueError):
            opciones = {}
            logger.warning("No se pudieron parsear las opciones de limpieza; usando defaults.")

        filename = secure_filename(file.filename)
        filepath = UPLOAD_FOLDER / filename
        file.save(str(filepath))
        logger.info("Archivo recibido: %s (%.1f KB)", filename, filepath.stat().st_size / 1024)

        try:
            output_path = procesar_planilla(str(filepath), filename, opciones=opciones)
            output_filename = Path(output_path).name
            logger.info("Procesamiento exitoso → %s", output_filename)
            return jsonify({
                "success": True,
                "download_url": url_for("download_file", filename=output_filename),
            })
        except Exception as exc:
            logger.error("Error al procesar '%s': %s", filename, exc, exc_info=True)
            return jsonify({"error": str(exc)}), 500
        finally:
            # Eliminar archivo de entrada en cualquier caso (ya está cargado en memoria)
            try:
                filepath.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("No se pudo eliminar el archivo de entrada: %s", exc)

    return render_template("index.html")


@app.route("/download/<filename>")
def download_file(filename: str):
    safe_path = UPLOAD_FOLDER / secure_filename(filename)

    if not safe_path.exists():
        return "Archivo no encontrado.", 404

    @after_this_request
    def _cleanup(response):
        try:
            safe_path.unlink(missing_ok=True)
            logger.info("Archivo de salida eliminado tras descarga: %s", filename)
        except OSError as exc:
            logger.warning("No se pudo eliminar el archivo de salida: %s", exc)
        return response

    return send_file(str(safe_path), as_attachment=True)


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=debug, port=port)
