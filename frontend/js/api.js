/* =============================================================================
   api.js — única camada que fala com a API Flask.
   Mantém exatamente os endpoints e o formato de dados já usados pelo
   app.js original. Nenhuma rota nova foi inventada aqui.
   ========================================================================== */

const API = (() => {
  const BASE = "/api";

  async function requisicao(caminho, opcoes) {
    const resp = await fetch(`${BASE}${caminho}`, opcoes);
    let dados = null;
    try {
      dados = await resp.json();
    } catch (erro) {
      dados = null;
    }
    return { ok: resp.ok, status: resp.status, dados };
  }

  return {
    // RF05 — autocompletação por prefixo.
    buscarSugestoes(prefixo, limite = 10) {
      return requisicao(`/tags/search?q=${encodeURIComponent(prefixo)}&limit=${limite}`);
    },
    // RF04 — busca exata.
    buscarTag(tag) {
      return requisicao(`/tags/${encodeURIComponent(tag)}`);
    },
    // RF06 — listagem completa (in-order).
    listarTags() {
      return requisicao(`/tags`);
    },
    // RF01 / RF08 — inserção (cria ou incrementa uso).
    inserirTag(tag, descricao) {
      return requisicao(`/tags`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tag, description: descricao }),
      });
    },
    // RF03 — remoção (bloqueada pela RN02 quando uso > 0).
    removerTag(tag) {
      return requisicao(`/tags/${encodeURIComponent(tag)}`, { method: "DELETE" });
    },
    // RF07 — associação/desassociação de tópicos.
    usarTag(tag) {
      return requisicao(`/tags/${encodeURIComponent(tag)}/use`, { method: "POST" });
    },
    desusarTag(tag) {
      return requisicao(`/tags/${encodeURIComponent(tag)}/unuse`, { method: "POST" });
    },
    // RF10 — métricas agregadas da árvore.
    metricas() {
      return requisicao(`/metrics`);
    },
    // RF09 — estrutura da árvore para a área acadêmica/visualizador.
    arvore() {
      return requisicao(`/avl`);
    },
    // Cenário obrigatório aula1..aula20.
    carregarCenario() {
      return requisicao(`/seed`, { method: "POST" });
    },
    // Limpa o dicionário para recomeçar a demonstração.
    reiniciar() {
      return requisicao(`/reset`, { method: "POST" });
    },
  };
})();
