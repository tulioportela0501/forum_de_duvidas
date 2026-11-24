"""Fábrica da aplicação Flask (usada pelo servidor local e pela função serverless da Vercel)."""
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from forum.auth import bp as auth_bp, origem_permitida
from forum.config import carregar_config
from forum.db import DbError, criar_db
from forum.repo import Repositorio
from forum.routes import bp as api_bp
from forum.service import ServicoForum
from forum.usuarios import bp as usuarios_bp
from forum.admin import bp as admin_bp
from forum.perfis import bp as perfis_bp
from forum.grupos import bp as grupos_bp


def create_app(overrides=None):
    cfg = carregar_config(overrides)
    app = Flask(__name__, static_folder=cfg['PUBLIC_DIR'], static_url_path='')
    app.config.update(cfg)

    repo = Repositorio(criar_db(cfg))
    if cfg['AUTO_INIT_DB']:
        repo.inicializar()           # só local por padrão; no Turso use scripts/init_db.py
    app.extensions['repo'] = repo
    app.extensions['servico'] = ServicoForum(repo)

    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(perfis_bp)
    app.register_blueprint(grupos_bp)

    @app.get('/')
    def index():                      # local; na Vercel o public/ é servido pela CDN
        return send_from_directory(app.static_folder, 'index.html')

    @app.after_request
    def cabecalhos(resp):
        origem = request.headers.get('Origin', '')
        if origem and origem_permitida(origem):
            resp.headers['Access-Control-Allow-Origin'] = origem
            resp.headers['Access-Control-Allow-Credentials'] = 'true'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRF-Token'
            resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PATCH, DELETE, OPTIONS'
            resp.headers['Vary'] = 'Origin'
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('Referrer-Policy', 'same-origin')
        resp.headers.setdefault('X-Frame-Options', 'DENY')
        if request.path.startswith('/api/'):
            resp.headers['Cache-Control'] = 'no-store'
        return resp

    @app.errorhandler(HTTPException)
    def erro_http(e):
        if request.path.startswith('/api/'):
            return jsonify(erro=e.description or e.name), e.code
        return e

    @app.errorhandler(DbError)
    def erro_banco(e):
        app.logger.error('Erro de banco: %s', e)
        return jsonify(erro='Banco de dados indisponível. Tente novamente em instantes.'), 503

    @app.errorhandler(Exception)
    def erro_interno(e):
        app.logger.exception('Erro interno')
        return jsonify(erro='Erro interno do servidor.'), 500

    return app
