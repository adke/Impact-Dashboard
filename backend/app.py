import os
from pathlib import Path

from flask import Flask, send_from_directory
from flask_cors import CORS

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def create_app():
    app = Flask(__name__, static_folder=str(FRONTEND_DIST), static_url_path="")

    CORS(app, origins=["http://localhost:5173", "http://localhost:5174"])

    from routes import bp
    app.register_blueprint(bp, url_prefix="/api")

    from cache import start_background_refresh
    start_background_refresh()

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        file_path = FRONTEND_DIST / path
        if path and file_path.is_file():
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5001)
