"""X DOWNLOADER - Secure Flask application factory."""

from flask import Flask
from flask_cors import CORS
import os

from app.core.config import Config
from app.routes import register_routes


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config_class)

    # Restrictive CORS for local development; tighten for production
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": app.config.get("CORS_ORIGINS", ["http://localhost:5000", "http://127.0.0.1:5000"]),
                "methods": ["GET", "POST", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type"],
            }
        },
    )

    # Ensure directories exist
    os.makedirs(app.config["DOWNLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["TEMP_FOLDER"], exist_ok=True)
    os.makedirs(app.config["DATA_FOLDER"], exist_ok=True)

    register_routes(app)
    return app
