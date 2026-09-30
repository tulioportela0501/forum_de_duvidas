"""Ponto de entrada do backend.  Uso:  python app.py   (http://127.0.0.1:5000)

O mesmo servidor entrega a API (/api/...) e o frontend (../frontend), então não há problema de CORS."""
import os
import re

from flask import Flask, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException

from admin_auth import bp as admin_bp
from config import carregar_config
from database import Repositorio
from routes import bp as api_bp
from service import ServicoForum

_LOCAL = re.compile(r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$')


def create_app(overrides=None):
    cfg = carregar_config(overrides)
    app = Flask(__name__, static_folder=cfg['FRONTEND_DIR'], static_url_path='')
    app.config.update(cfg)

    repo = Repositorio(cfg['DB_PATH'])
    app.extensions['repo'] = repo
    app.extensions['servico'] = ServicoForum(repo)

    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    @app.get('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    @app.after_request
    def cabecalhos(resp):
        from flask import request
        origem = request.headers.get('Origin', '')
        if origem and (_LOCAL.match(origem) or origem in app.config['CORS_ORIGINS']):
            resp.headers['Access-Control-Allow-Origin'] = origem
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
            resp.headers['Vary'] = 'Origin'
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('Referrer-Policy', 'same-origin')
        if request.path.startswith('/api/'):
            resp.headers['Cache-Control'] = 'no-store'
        return resp

    @app.errorhandler(HTTPException)
    def erro_http(e):
        from flask import request
        if request.path.startswith('/api/'):
            return jsonify(erro=e.description or e.name), e.code
        return e

    @app.errorhandler(Exception)
    def erro_interno(e):
        app.logger.exception('Erro interno')
        return jsonify(erro='Erro interno do servidor.'), 500

    return app


if __name__ == '__main__':
    app = create_app()
    print('\n' + '=' * 62)
    print(' Fórum AVL rodando em http://127.0.0.1:%s' % os.environ.get('PORT', 5000))
    print(' Código de cadastro de administrador (%s):' % app.config['CODIGO_ADMIN_ORIGEM'])
    print('   ', app.config['CODIGO_ADMIN'])
    print('=' * 62 + '\n')
    # threaded=True ok: a AVL em memória é protegida por trava. Não use vários processos.
    app.run(host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', 5000)),
            debug=os.environ.get('FLASK_DEBUG') == '1', threaded=True)
