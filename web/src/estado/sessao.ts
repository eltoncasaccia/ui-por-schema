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
  /** A composição com o diálogo de compartilhar aberto, venha de que tela vier. */
  compartilhando: Composicao | null
}

const VAZIO: Estado = {
  conversa: [], composicoes: {}, noWorkspace: null,
  fixadas: [], traces: [], pensando: false, compartilhando: null,
}

let estado: Estado = VAZIO
const ouvintes = new Set<() => void>()

function definir(parcial: Partial<Estado>) {
  estado = { ...estado, ...parcial }
  ouvintes.forEach((o) => o())
}

export const sessao = {
  ler: () => estado,
  // Arrow, e não método abreviado: os dois são passados sem `this`
  // (`useSyncExternalStore`, `onClick`). Arrow declara que não dependem dele.
  ouvir: (o: () => void) => { ouvintes.add(o); return () => ouvintes.delete(o) },

  pergunta(texto: string) {
    definir({ conversa: [...estado.conversa, { papel: 'usuario', texto }], pensando: true })
  },
  falhou(texto: string) {
    definir({ conversa: [...estado.conversa, { papel: 'erro', texto }], pensando: false })
  },
  nota(texto: string) {
    definir({ conversa: [...estado.conversa, { papel: 'nota', texto }], pensando: false })
  },
  /** Abre no workspace. Usado pela navegação e pelas views fixadas. */
  compos(c: Composicao) {
    definir({ composicoes: { ...estado.composicoes, [c.id]: c }, noWorkspace: c.id, pensando: false })
  },

  /**
   * Resposta do assistente: entra na CONVERSA e NÃO no workspace.
   *
   * Renderizar nos dois lugares foi um erro de comportamento reportado em uso:
   * o assistente passava por cima do que a pessoa estava olhando. Ele propõe;
   * quem decide o que ocupa o workspace é ela.
   */
  responde(c: Composicao, trace?: Trace, pergunta = '') {
    definir({
      composicoes: { ...estado.composicoes, [c.id]: c },
      conversa: [...estado.conversa, { papel: 'assistente', composicaoId: c.id }],
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
  limpar: () => { definir({ conversa: [], pensando: false }) },
  /** Abre — ou fecha, com `null` — o diálogo de compartilhar, de qualquer tela,
   *  sem callback atravessando o roteador. */
  compartilhar: (c: Composicao | null) => { definir({ compartilhando: c }) },
  reset() { estado = VAZIO; ouvintes.forEach((o) => o()) },
}

/**
 * A composição de uma tela de rota, no mesmo formato que o menu e o assistente
 * produzem — é o que deixa fixar e compartilhar funcionarem igual em toda tela.
 */
export function composicaoDaTela(titulo: string, blocos: Bloco[]): Composicao {
  const viewKey = viewKeyLocal(blocos)
  return {
    id: `tela-${viewKey}`,
    titulo,
    origem: 'sistema',
    blocos,
    schema: { versao: 1, blocos: blocos.map((b) => ({ tipo: b.tipo, params: b.params })) },
    viewKey,
  }
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
