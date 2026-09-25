/**
 * Cliente HTTP. A única porta do navegador para o servidor.
 *
 * Nenhuma view importa este módulo — quem busca dado é o motor de render
 * (ADR-0007). Uma view recebe `vm` e nada mais.
 */

export type Resposta<T> =
  | { ok: true; dados: T; meta: Record<string, unknown> }
  | { ok: false; erro: { codigo: string; mensagem: string } }

export class ErroApi extends Error {
  constructor(readonly codigo: string, mensagem: string) {
    super(mensagem)
  }
}

function tokenCsrf(): string {
  const m = document.cookie.match(/(?:^|;\s*)csrf=([^;]+)/)
  return m?.[1] ?? ''
}

async function chamarComMeta<T>(
  caminho: string,
  init?: RequestInit,
): Promise<{ dados: T; meta: Record<string, unknown> }> {
  const r = await fetch(caminho, {
    ...init,
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      // Dupla submissão: um site de terceiro consegue disparar a requisição,
      // mas não consegue LER o cookie para montar este header (ADR-0019).
      ...(init?.method && init.method !== 'GET' ? { 'X-CSRF-Token': tokenCsrf() } : {}),
      ...init?.headers,
    },
  })
  const corpo = (await r.json()) as Resposta<T>
  if (!corpo.ok) throw new ErroApi(corpo.erro.codigo, corpo.erro.mensagem)
  return { dados: corpo.dados, meta: corpo.meta }
}

async function chamar<T>(caminho: string, init?: RequestInit): Promise<T> {
  return (await chamarComMeta<T>(caminho, init)).dados
}

// T-050: o etag mais recente lido para cada (tipo, params) — a chave que uma
// escrita seguinte do MESMO bloco usa no `If-Match`. Não é cache de dado,
// só do metadado de concorrência; o dado em si continua vindo do TanStack
// Query, sem duplicação (ADR-0008).
const etagPorChave = new Map<string, string>()
function chaveEtag(tipo: string, params: Record<string, unknown>): string {
  return `${tipo}:${JSON.stringify(params)}`
}

export interface Persona { email: string; nome: string; papel: string }
export interface Eu { id: string; nome: string; papel: string | null; unidades: string[]; permissoes: string[] }
export interface ParamInfo { valores?: string[]; tipo?: string; obrigatorio: boolean }
export type FormatoExportacao = 'csv' | 'xlsx' | 'pdf'

export interface ComandoDoBloco { endpoint: string; confirm: boolean; idempotent: boolean }
export interface EntradaCatalogo {
  id: string
  label: string
  description: string
  examples: string[]
  params: Record<string, ParamInfo>
  /** T-054: o servidor gera arquivo deste componente. Só da borda, nunca do prompt. */
  exportavel?: boolean
  /**
   * T-057: o mesmo `comandos` que um `Bloco` composto pelo assistente ou por
   * uma view salva já carrega — aqui para quem monta o `Bloco` de uma ROTA
   * tradicional (`TelaOperacao`, `TelaSaida`), que nunca passa pelas duas
   * rotas que normalmente anexam isto (`bloco_resposta`, CONTRATOS §6/§8).
   */
  comandos?: Record<string, ComandoDoBloco>
}
export interface Bloco {
  tipo: string
  params: Record<string, unknown>
  tamanho: string
  // Só presente quando o componente DECLARA `commands` (CONTRATOS §6/§8) —
  // ausência, não objeto vazio, é o que distingue leitura de escrita.
  comandos?: Record<string, ComandoDoBloco>
}
export interface TraceApi {
  origem: string; modelo: string; modo: string; schema_valido: boolean
  aceitos: string[]; rejeitados: [string, string][]
  tokens_entrada: number; ms_ate_primeiro_token: number; erro: string | null
  provedor_efetivo?: string
}
/** Opção de esclarecimento: id validado no servidor, rótulo do catálogo — nunca texto do modelo. */
export interface OpcaoEsclarecer { id: string; label: string }
export interface Composicao { schema: unknown; blocos: Bloco[]; trace: TraceApi; esclarecer?: OpcaoEsclarecer[] }

export interface Destinatario { id: string; nome: string; papel: string }
export interface Recebida {
  id: number; view_id: string; mensagem: string | null; de: string; criado_em: string
}
export interface ViewAberta { view_id: string; schema: unknown; blocos: Bloco[] }
export interface UsuarioAdmin {
  id: string; nome: string; email: string; papel: string | null; unidades: string[]; ativo: boolean
}
export type MudancaUsuario = Partial<Pick<UsuarioAdmin, 'papel' | 'unidades' | 'ativo'>>

export const api = {
  // T-038 — fora do catálogo. POST, não PATCH: a varredura do CA-08 recusa
  // verbo que substitui ou apaga em toda a borda.
  usuarios: () => chamar<UsuarioAdmin[]>('/api/usuarios'),
  alterarUsuario: (id: string, mudanca: MudancaUsuario) =>
    chamar<Required<MudancaUsuario>>(`/api/usuarios/${id}`, {
      method: 'POST', body: JSON.stringify(mudanca),
    }),
  criarView: (titulo: string, schema: unknown) =>
    chamar<{ view_id: string; view_key: string }>('/api/views', {
      method: 'POST', body: JSON.stringify({ titulo, schema }),
    }),
  abrirView: (viewId: string) => chamar<ViewAberta>(`/api/views/${viewId}`),
  destinatarios: (schema: unknown) =>
    chamar<Destinatario[]>('/api/destinatarios', {
      method: 'POST', body: JSON.stringify({ schema }),
    }),
  compartilhar: (view_id: string, para: string, mensagem?: string) =>
    chamar<unknown>('/api/compartilhamentos', {
      method: 'POST', body: JSON.stringify({ view_id, para, mensagem: mensagem ?? null }),
    }),
  recebidas: () => chamar<Recebida[]>('/api/compartilhamentos'),
  personas: () => chamar<Persona[]>('/api/auth/demo'),
  entrar: (email: string, senha: string) =>
    chamar<Eu>('/api/auth/entrar', { method: 'POST', body: JSON.stringify({ email, senha }) }),
  sair: () => chamar<unknown>('/api/auth/sair', { method: 'POST' }),
  eu: () => chamar<Eu>('/api/auth/eu'),
  catalogo: () => chamar<EntradaCatalogo[]>('/api/catalogo'),
  /**
   * T-054: o arquivo sai do servidor, com a mesma autorização da leitura. A
   * resposta boa é binária; a ruim é o envelope de erro de sempre.
   */
  exportar: async (
    id: string, params: Record<string, unknown>, formato: FormatoExportacao,
  ): Promise<{ arquivo: Blob; nome: string }> => {
    const r = await fetch(`/api/componentes/${id}/exportar`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': tokenCsrf() },
      body: JSON.stringify({ params, formato }),
    })
    if (!r.ok) {
      const corpo = (await r.json()) as Resposta<unknown>
      if (!corpo.ok) throw new ErroApi(corpo.erro.codigo, corpo.erro.mensagem)
      throw new ErroApi('invalido', 'Não foi possível exportar.')
    }
    const nome = /filename="([^"]+)"/.exec(r.headers.get('Content-Disposition') ?? '')?.[1]
    return { arquivo: await r.blob(), nome: nome ?? `exportacao.${formato}` }
  },
  compor: async (pergunta: string): Promise<Composicao> => {
    const r = await fetch('/api/assistente/compor', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': tokenCsrf() },
      body: JSON.stringify({ pergunta }),
    })
    const corpo = (await r.json()) as Resposta<{ schema: unknown; blocos: Bloco[] }>
    if (!corpo.ok) throw new ErroApi(corpo.erro.codigo, corpo.erro.mensagem)
    // O trace vem em `meta`: é instrumentação da execução, não dado da view.
    return { ...corpo.dados, trace: corpo.meta['trace'] as TraceApi }
  },
  dados: async <T,>(id: string, params: Record<string, unknown>, cursor?: string | null) => {
    const { dados, meta } = await chamarComMeta<T>(`/api/componentes/${id}/dados`, {
      method: 'POST',
      // `pagina` vai FORA de `params`: paginação é transporte, e o modelo
      // nunca escolhe quantas linhas cabem nem por onde continuar.
      body: JSON.stringify({ params, pagina: { limite: 20, cursor: cursor ?? null } }),
    })
    // Só a PRIMEIRA página tem o etag da entidade-alvo do comando — páginas
    // seguintes (cursor != null) são continuação de uma listagem e não têm
    // por que sobrescrever o etag já guardado.
    const etag = meta['etag']
    if (cursor == null && typeof etag === 'string') etagPorChave.set(chaveEtag(id, params), etag)
    return dados
  },
  etagAtual: (tipo: string, params: Record<string, unknown>) => etagPorChave.get(chaveEtag(tipo, params)),
  // `endpoint` já vem completo em `Bloco.comandos` (CONTRATOS §6/§8) — o
  // cliente só chama, nunca monta a rota. `chave` é gerada por quem dispara,
  // não aqui: uma retentativa da MESMA tentativa reaproveita a mesma chave.
  comando: <T,>(endpoint: string, corpo: Record<string, unknown>, chave: string, etag?: string) =>
    chamar<T>(endpoint, {
      method: 'POST',
      headers: { 'Idempotency-Key': chave, ...(etag ? { 'If-Match': etag } : {}) },
      body: JSON.stringify(corpo),
    }),
}
