const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1'

function getToken() {
  return localStorage.getItem('milkshow_token') || ''
}

async function req(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401) {
    localStorage.removeItem('milkshow_token')
    window.location.href = '/app/login'
    return
  }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Erro na requisição')
  return data
}

export const api = {
  // Auth
  googleLogin:          (id_token)       => req('POST', '/auth/google',     { id_token }),

  // Dashboard
  dashboard:            ()               => req('GET',  '/dashboard'),

  // Animais
  animais:              ()               => req('GET',  '/animais'),
  adicionarAnimal:      (body)           => req('POST', '/animais',          body),
  removerAnimal:        (id)             => req('DELETE', `/animais/${id}`),

  // Produção
  producao:             (dias = 7)       => req('GET',  `/producao?dias=${dias}`),
  producaoPorAnimal:    (nome, dias=30)  => req('GET',  `/producao/animal/${encodeURIComponent(nome)}?dias=${dias}`),
  registrarProducao:    (body)           => req('POST', '/producao',         body),
  removerProducao:      (id)             => req('DELETE', `/producao/${id}`),

  // Financeiro
  financeiro:           (dias = 30)      => req('GET',  `/financeiro?dias=${dias}`),
  resumoFinanceiro:     (dias = 30)      => req('GET',  `/financeiro/resumo?dias=${dias}`),
  registrarFinanceiro:  (body)           => req('POST', '/financeiro',       body),
  atualizarFinanceiro:  (id, body)       => req('PATCH', `/financeiro/${id}`, body),
  removerFinanceiro:    (id)             => req('DELETE', `/financeiro/${id}`),

  // Sanitário
  sanitario:            (dias = 90)      => req('GET',  `/sanitario?dias=${dias}`),
  registrarSanitario:   (body)           => req('POST', '/sanitario',        body),
  executarSanitario:    (id)             => req('PATCH', `/sanitario/${id}/executar`),

  // Estoque / Armazém
  estoque:              ()               => req('GET',    '/estoque'),
  registrarEstoque:     (body)           => req('POST',   '/estoque',            body),
  atualizarEstoque:     (id, body)       => req('PATCH',  `/estoque/${id}`,      body),
  removerEstoque:       (id)             => req('DELETE', `/estoque/${id}`),

  // Config
  config:               ()               => req('GET',  '/config'),
  salvarConfig:         (body)           => req('POST', '/config',           body),

  // Curva de lactação por animal
  lactacao:             (nome, dias=120) => req('GET',  `/lactacao/${encodeURIComponent(nome)}?dias=${dias}`),

  // Lotes de ração
  lotesRacao:           ()               => req('GET',  '/lotes_racao'),

  // Agenda semanal
  agenda:               (dias = 7)       => req('GET',  `/agenda?dias=${dias}`),

  // Custo por litro (KPI mensal)
  custoLitro:           ()               => req('GET',  '/custo_litro'),

  // Relatório mensal PDF — retorna URL autenticada para download direto
  relatorioMensalUrl:   (mes = '')       => `${BASE}/relatorio_mensal${mes ? `?mes=${mes}` : ''}`,
  relatorioMensal: async (mes = '') => {
    const url = `${BASE}/relatorio_mensal${mes ? `?mes=${mes}` : ''}`
    const res = await fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } })
    if (!res.ok) throw new Error('Erro ao gerar relatório')
    return res.blob()
  },

  // Ranking de rentabilidade
  ranking:              (dias = 30)      => req('GET',  `/ranking?dias=${dias}`),

  // SSE — atualizações em tempo real
  openEventSource: () => {
    const token = getToken()
    return new EventSource(`${BASE}/eventos?token=${encodeURIComponent(token)}`)
  },
}
