"""Flask application factory."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from app.core import get_settings
from app.models import db

# Load workflow registry definitions on startup
import app.workflows  # noqa: F401

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def _ensure_instance_path(app: Flask) -> None:
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass


def create_app() -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    settings = get_settings()
    app.config.update(settings.as_flask_config())
    app.config["APP_SETTINGS"] = settings

    # Ensure instance folder exists
    _ensure_instance_path(app)

    # Initialize extensions
    db.init_app(app)
    CORS(app)

    # Register blueprints
    from app.web import web_bp
    from app.api import api_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

    # Database initialization command
    @app.cli.command("init-db")
    def init_db():
        """Initialize the database."""
        # Ensure instance folder exists
        import os

        try:
            os.makedirs(app.instance_path, exist_ok=True)
        except OSError:
            pass

        with app.app_context():
            db.create_all()
            print("✓ Database initialized successfully")

            # Add sample lookup data
            from app.models import LookupData

            sample_data = [
                # Organizations
                {
                    "field": "Organization",
                    "value": "TradeX Corp",
                    "abbreviation": "TX",
                },
                {"field": "Organization", "value": "TradeX IT", "abbreviation": "TIT"},
                # LOBs
                {"field": "LOB", "value": "Digital Platform", "abbreviation": "DP"},
                {"field": "LOB", "value": "Supply Chain", "abbreviation": "SC"},
                {"field": "LOB", "value": "Finance", "abbreviation": "FIN"},
                {"field": "LOB", "value": "Human Resources", "abbreviation": "HR"},
                # Environments
                {"field": "Environment", "value": "Development", "abbreviation": "DEV"},
                {"field": "Environment", "value": "Testing", "abbreviation": "TEST"},
                {"field": "Environment", "value": "Staging", "abbreviation": "STG"},
                {"field": "Environment", "value": "Production", "abbreviation": "PROD"},
                # Regions
                {"field": "Region", "value": "East US", "abbreviation": "EUS"},
                {"field": "Region", "value": "West US", "abbreviation": "WUS"},
                {"field": "Region", "value": "Central US", "abbreviation": "CUS"},
                {"field": "Region", "value": "Canada Central", "abbreviation": "CAC"},
            ]

            for data in sample_data:
                existing = LookupData.query.filter_by(
                    field=data["field"], value=data["value"]
                ).first()
                if not existing:
                    lookup = LookupData(**data)
                    db.session.add(lookup)

            db.session.commit()
            print("✓ Sample lookup data added")

    # Context processor for templates
    @app.context_processor
    def inject_user():
        """Inject user information into all templates."""
        from flask import session

        return {"current_user": session.get("user_email")}

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors."""
        return {"error": "Resource not found"}, 404

    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 errors."""
        return {"error": "Internal server error"}, 500

    return app


# Create app instance
app = create_app()
