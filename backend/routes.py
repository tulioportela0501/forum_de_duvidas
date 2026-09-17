# =============================================================================
# routes.py
# -----------------------------------------------------------------------------
# Camada HTTP. De proposito ela e FINA: recebe a requisicao, chama o
# TagService e devolve JSON. Nenhuma regra de negocio mora aqui.
# =============================================================================

from flask import Blueprint, jsonify, request

from .models import TagValidationError
from .services import TagService

api = Blueprint("api", __name__)

# Instancia unica do servico. Como o MVP guarda tudo em memoria (item 13),
# essa instancia vive enquanto o processo Flask estiver rodando.
service = TagService()


@api.errorhandler(TagValidationError)
def handle_validation_error(error):
    # Traduz violacao de regra de negocio em HTTP 400.
    return jsonify({"error": str(error)}), 400


# -----------------------------------------------------------------------------
# RF01 / RF07 / RF08 — POST /api/tags
# -----------------------------------------------------------------------------
@api.post("/tags")
def create_tag():
    # Cadastra uma tag nova ou incrementa o uso de uma existente.
    data = request.get_json(silent=True) or {}
    try:
        result = service.add_tag(data.get("tag"), data.get("description", ""))
    except TagValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    # 201 quando um no novo nasceu; 200 quando so incrementamos o contador.
    return jsonify(result), 201 if result["created"] else 200


# -----------------------------------------------------------------------------
# RF06 — GET /api/tags
# -----------------------------------------------------------------------------
@api.get("/tags")
def list_tags():
    # Listagem alfabetica completa (percurso in-order).
    return jsonify({"tags": service.list_tags()})


# -----------------------------------------------------------------------------
# RF05 — GET /api/tags/search?q=
# -----------------------------------------------------------------------------
@api.get("/tags/search")
def search_tags():
    # Endpoint consumido pelo autocomplete do frontend.
    query = request.args.get("q", "")
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        limit = 10
    return jsonify({"query": query, "suggestions": service.search_prefix(query, limit)})


# -----------------------------------------------------------------------------
# RF04 — GET /api/tags/<tag>
# -----------------------------------------------------------------------------
@api.get("/tags/<path:tag>")
def get_tag(tag):
    # Busca exata, case-insensitive (RN01).
    found = service.get_tag(tag)
    if found is None:
        return jsonify({"error": "Tag nao encontrada."}), 404
    return jsonify({"tag": found})


# -----------------------------------------------------------------------------
# RF07 — POST /api/tags/<tag>/use  e  /unuse
# -----------------------------------------------------------------------------
@api.post("/tags/<path:tag>/use")
def use_tag(tag):
    # Simula a associacao da tag a um novo topico (UC01).
    updated = service.increment_usage(tag)
    if updated is None:
        return jsonify({"error": "Tag nao encontrada."}), 404
    return jsonify({"tag": updated})


@api.post("/tags/<path:tag>/unuse")
def unuse_tag(tag):
    # Simula a exclusao de um topico que usava a tag (UC03).
    # Quando o contador chega a zero, a tag passa a ser removivel (RN02).
    updated = service.decrement_usage(tag)
    if updated is None:
        return jsonify({"error": "Tag nao encontrada."}), 404
    return jsonify({"tag": updated})


# -----------------------------------------------------------------------------
# RF03 + RN02 — DELETE /api/tags/<tag>
# -----------------------------------------------------------------------------
@api.delete("/tags/<path:tag>")
def delete_tag(tag):
    # A remocao pode ser recusada pela RN02 (contador maior que zero).
    try:
        service.remove_tag(tag)
    except TagValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"removed": tag})


# -----------------------------------------------------------------------------
# RF09 — GET /api/avl
# -----------------------------------------------------------------------------
@api.get("/avl")
def avl_view():
    # Estrutura completa da arvore para a area de debug academico (UC04).
    return jsonify(service.tree_view())


# -----------------------------------------------------------------------------
# RF10 — GET /api/metrics
# -----------------------------------------------------------------------------
@api.get("/metrics")
def metrics():
    # Altura, numero de nos, rotacoes e validacao do RNF05.
    return jsonify(service.metrics())


# -----------------------------------------------------------------------------
# Utilitarios de apresentacao (nao sao requisito, mas ajudam na demo)
# -----------------------------------------------------------------------------
@api.post("/reset")
def reset():
    # Limpa o dicionario para demonstracoes.
    service.reset()
    return jsonify({"reset": True})


@api.post("/seed")
def seed():
    # Carrega o cenario obrigatorio do item 5.4: aula1..aula20 inseridas em
    # ordem alfabetica estrita. Permite mostrar ao vivo, na interface, que a
    # arvore NAO degenerou em lista encadeada.
    service.reset()
    # sorted() aqui ordena apenas a ENTRADA do teste (para garantir a ordem
    # alfabetica estrita exigida pelo documento). A estrutura de dados do
    # sistema continua sendo exclusivamente a AVL.
    for tag in sorted(f"aula{i}" for i in range(1, 21)):
        service.add_tag(tag, "Tag do cenario de teste obrigatorio")
    return jsonify({"seeded": 20, "metrics": service.metrics()})
