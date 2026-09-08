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

async function chamar<T>(caminho: string, init?: RequestInit): Promise<T> {
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
  return corpo.dados
}

export interface Persona { email: string; nome: string; papel: string }
export interface Eu { id: string; nome: string; papel: string | null; unidades: string[]; permissoes: string[] }
export interface ParamInfo { valores?: string[]; tipo?: string; obrigatorio: boolean }
export interface EntradaCatalogo {
  id: string
  label: string
  description: string
  examples: string[]
  params: Record<string, ParamInfo>
}
export interface Bloco { tipo: string; params: Record<string, unknown>; tamanho: string }
export interface TraceApi {
  origem: string; modelo: string; modo: string; schema_valido: boolean
  aceitos: string[]; rejeitados: [string, string][]
  tokens_entrada: number; ms_ate_primeiro_token: number; erro: string | null
  provedor_efetivo?: string
}
export interface Composicao { schema: unknown; blocos: Bloco[]; trace: TraceApi }

export interface Destinatario { id: string; nome: string; papel: string }
export interface Recebida {
  id: number; view_id: string; mensagem: string | null; de: string; criado_em: string
}
export interface ViewAberta { view_id: string; schema: unknown; blocos: Bloco[] }

export const api = {
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
  dados: <T,>(id: string, params: Record<string, unknown>, cursor?: string | null) =>
    chamar<T>(`/api/componentes/${id}/dados`, {
      method: 'POST',
      // `pagina` vai FORA de `params`: paginação é transporte, e o modelo
      // nunca escolhe quantas linhas cabem nem por onde continuar.
      body: JSON.stringify({ params, pagina: { limite: 20, cursor: cursor ?? null } }),
    }),
}
