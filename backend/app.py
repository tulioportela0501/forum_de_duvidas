# =============================================================================
# app.py
# -----------------------------------------------------------------------------
# Fabrica da aplicacao Flask. Usamos o padrao create_app() porque ele permite
# criar instancias isoladas nos testes sem depender de um objeto global.
# =============================================================================

import os

from flask import Flask, send_from_directory

from .routes import api

# Caminho absoluto da pasta frontend (fica fora de backend/, por isso subimos
# um nivel a partir deste arquivo).
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


def create_app():
    # Cria e configura a aplicacao Flask.
    app = Flask(__name__, static_folder=None)

    # Todas as rotas de API ficam sob o prefixo /api, conforme o item 12.
    app.register_blueprint(api, url_prefix="/api")

    @app.get("/")
    def index():
        # Serve a interface web (frontend/index.html).
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<path:filename>")
    def static_files(filename):
        # Serve CSS e JS do frontend. Mantemos o servidor de estaticos simples
        # porque no MVP nao ha build step nem framework de frontend.
        return send_from_directory(FRONTEND_DIR, filename)

    return app
