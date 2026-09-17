# =============================================================================
# models.py
# -----------------------------------------------------------------------------
# Camada de modelo: normalizacao, validacao e serializacao das tags.
#
# Deixamos essas funcoes separadas da AVL de proposito. Assim, quando o
# projeto ganhar SQLite/MySQL/PostgreSQL, a persistencia reaproveita as mesmas
# regras de normalizacao sem duplicar logica.
# =============================================================================

# Tamanho minimo exigido pela RN04.
MIN_TAG_LENGTH = 2


class TagValidationError(Exception):
    # Excecao usada para sinalizar violacao de regra de negocio.
    # A camada de rotas traduz isso em HTTP 400 com mensagem amigavel.
    pass


def normalize(tag):
    # Converte a tag para a forma usada em TODAS as comparacoes da arvore.
    #
    # Aplica a RN01: a comparacao e case-insensitive. Fazemos casefold() em
    # vez de lower() porque casefold trata corretamente casos especiais de
    # outros alfabetos (ex.: o "ß" alemao). Tambem removemos espacos das
    # pontas, que sao sempre digitacao acidental do usuario.
    return tag.strip().casefold()


def validate_tag(tag):
    # Valida a tag antes de qualquer escrita na arvore.
    #
    # Regras aplicadas aqui:
    #   - RN04: tags com menos de 2 caracteres sao rejeitadas, para evitar
    #     poluicao do dicionario com lixo tipo "a" ou "x".
    #   - tag vazia ou nao-string tambem e rejeitada.
    if tag is None or not isinstance(tag, str):
        raise TagValidationError("A tag precisa ser um texto.")

    cleaned = tag.strip()

    if len(cleaned) < MIN_TAG_LENGTH:
        raise TagValidationError(
            f"A tag precisa ter pelo menos {MIN_TAG_LENGTH} caracteres (RN04)."
        )

    return cleaned


def serialize_node(node):
    # Converte um no da AVL no formato JSON consumido pelo frontend.
    #
    # Repare que devolvemos 'tag' com a capitalizacao ORIGINAL do cadastro,
    # e nao a chave normalizada. Isso fecha a segunda metade da RN01:
    # comparar sem case, mas exibir com case.
    return {
        "tag": node.display_name,
        "key": node.key,
        "description": node.description,
        "usage_count": node.usage_count,
        "height": node.height,
    }
