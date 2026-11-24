"""Servidor local:  python run_local.py   ->  http://127.0.0.1:5000 (API + frontend de public/)."""
import os

from forum import create_app

app = create_app()

if __name__ == '__main__':
    cfg = app.config
    banco = 'Turso (remoto)' if cfg['TURSO_DATABASE_URL'] else 'SQLite local (%s)' % cfg['LOCAL_DB_PATH']
    print('\n' + '=' * 64)
    print(' Fórum AVL em http://127.0.0.1:%s' % os.environ.get('PORT', 5000))
    print(' Banco:', banco)
    print(' Primeiro acesso: abra o endereço acima e crie o administrador principal.')
    print('=' * 64 + '\n')
    app.run(host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', 5000)),
            debug=os.environ.get('FLASK_DEBUG') == '1')
