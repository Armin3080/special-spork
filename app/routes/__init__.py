"""Route registration."""

from app.routes.api import api_bp
from app.routes.main import main_bp


def register_routes(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
