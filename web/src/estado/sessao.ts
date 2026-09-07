/**
 * Estado de sessão do assistente — o único store fora do TanStack Query.
 *
 * ADR-0008: dado de servidor vive no Query; isto aqui é o que nenhum servidor
 * conhece — a conversa em andamento, o que está no workspace, o que foi fixado.
 */
import { useSyncExternalStore } from 'react'
import type { Bloco } from '../api'

export interface Trace {
  origem: string
  modelo: string
  modo: string
  schema_valido: boolean
  aceitos: string[]
  rejeitados: [string, string][]
  tokens_entrada: number
  ms_ate_primeiro_token: number
  erro: string | null
  provedor_efetivo?: string
}

export interface Composicao {
  id: string
  titulo: string
  origem: 'assistente' | 'sistema'
  blocos: Bloco[]
  schema: unknown
  viewKey: string
}

export type Mensagem =
  | { papel: 'usuario'; texto: string }
  | { papel: 'assistente'; composicaoId: string }
  | { papel: 'erro'; texto: string }
  | { papel: 'nota'; texto: string }

interface Estado {
  conversa: Mensagem[]
  composicoes: Record<string, Composicao>
  noWorkspace: string | null
  fixadas: { viewKey: string; titulo: string; blocos: Bloco[] }[]
  traces: { pergunta: string; trace: Trace; em: number }[]
  pensando: boolean
}

let estado: Estado = {
  conversa: [], composicoes: {}, noWorkspace: null,
  fixadas: [], traces: [], pensando: false,
}
const ouvintes = new Set<() => void>()

function definir(parcial: Partial<Estado>) {
  estado = { ...estado, ...parcial }
  ouvintes.forEach((o) => o())
}

export const sessao = {
  ler: () => estado,
  ouvir(o: () => void) { ouvintes.add(o); return () => ouvintes.delete(o) },

  pergunta(texto: string) {
    definir({ conversa: [...estado.conversa, { papel: 'usuario', texto }], pensando: true })
  },
  falhou(texto: string) {
    definir({ conversa: [...estado.conversa, { papel: 'erro', texto }], pensando: false })
  },
  nota(texto: string) {
    definir({ conversa: [...estado.conversa, { papel: 'nota', texto }], pensando: false })
  },
  compos(c: Composicao, trace?: Trace, pergunta = '') {
    definir({
      composicoes: { ...estado.composicoes, [c.id]: c },
      conversa: c.origem === 'assistente'
        ? [...estado.conversa, { papel: 'assistente', composicaoId: c.id }]
        : estado.conversa,
      noWorkspace: c.id,
      pensando: false,
      traces: trace ? [{ pergunta, trace, em: Date.now() }, ...estado.traces].slice(0, 20) : estado.traces,
    })
  },
  aoWorkspace(id: string) { definir({ noWorkspace: id }) },
  /** Chaveado pela viewKey, não pelo id da composição — foi o bug do favorito
   *  da v1: reabrir a mesma tela gerava id novo e a estrela voltava apagada. */
  fixar(c: Composicao) {
    const ja = estado.fixadas.some((f) => f.viewKey === c.viewKey)
    definir({
      fixadas: ja
        ? estado.fixadas.filter((f) => f.viewKey !== c.viewKey)
        : [...estado.fixadas, { viewKey: c.viewKey, titulo: c.titulo, blocos: c.blocos }],
    })
  },
  limpar() { definir({ conversa: [], pensando: false }) },
  reset() { estado = { conversa: [], composicoes: {}, noWorkspace: null, fixadas: [], traces: [], pensando: false }; ouvintes.forEach((o) => o()) },
}

export function useSessao(): Estado {
  return useSyncExternalStore(sessao.ouvir, sessao.ler, sessao.ler)
}

/** Hash estável do schema — mesma composição, mesma chave (ADR-0021). */
export function viewKeyLocal(blocos: Bloco[]): string {
  const canon = JSON.stringify(
    blocos.map((b) => ({
      tipo: b.tipo,
      params: Object.fromEntries(Object.entries(b.params).filter(([, v]) => v != null).sort()),
    })),
  )
  let h = 0
  for (let i = 0; i < canon.length; i++) h = (Math.imul(31, h) + canon.charCodeAt(i)) | 0
  return (h >>> 0).toString(16)
}
