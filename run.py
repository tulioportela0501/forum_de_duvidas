# =============================================================================
# run.py
# -----------------------------------------------------------------------------
# Ponto de entrada do sistema. Execute com:  python run.py
# =============================================================================

import os

from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    # A porta pode ser sobrescrita por variavel de ambiente (ver .env.example).
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    print(f"Forum Academico AVL rodando em http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=debug)
