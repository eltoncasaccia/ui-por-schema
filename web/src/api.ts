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
export interface Composicao { schema: unknown; blocos: Bloco[] }

export const api = {
  personas: () => chamar<Persona[]>('/api/auth/demo'),
  entrar: (email: string, senha: string) =>
    chamar<Eu>('/api/auth/entrar', { method: 'POST', body: JSON.stringify({ email, senha }) }),
  sair: () => chamar<unknown>('/api/auth/sair', { method: 'POST' }),
  eu: () => chamar<Eu>('/api/auth/eu'),
  catalogo: () => chamar<EntradaCatalogo[]>('/api/catalogo'),
  compor: (pergunta: string) =>
    chamar<Composicao>('/api/assistente/compor', {
      method: 'POST',
      body: JSON.stringify({ pergunta }),
    }),
  dados: <T,>(id: string, params: Record<string, unknown>) =>
    chamar<T>(`/api/componentes/${id}/dados`, {
      method: 'POST',
      body: JSON.stringify({ params }),
    }),
}
