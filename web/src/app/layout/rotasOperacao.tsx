/**
 * A tabela única das rotas de operação (T-031, ADR-0005 — "o mesmo componente
 * registrado serve à rota tradicional e ao assistente").
 *
 * Uma linha aqui alimenta DUAS coisas ao mesmo tempo: a entrada do roteador
 * (`Roteador.tsx`, que casa o path e extrai os params da URL) e a entrada da
 * navegação lateral (`shell/PainelNavegacao.tsx`, filtrada pelo catálogo DESTE
 * ator — ADR-0003). Uma tabela só, duas superfícies — o mesmo argumento do
 * componente, aplicado aqui à rota.
 */
import type { ComponentId } from '../../generated/componentes'
import { Icone } from '../../ui/icones'

export interface RotaOperacao {
  path: string
  componente: ComponentId
  rotulo: string
  sub: string
  icone: (p: { tamanho?: number }) => JSX.Element
  /** Constrói os params do componente a partir dos params da URL (`useParams`). */
  params: (urlParams: Readonly<Record<string, string | undefined>>) => Record<string, unknown>
  /**
   * Componentes adicionais que o catálogo do ator precisa ter para esta
   * entrada aparecer na navegação lateral. Existe porque `/quarentena` lista
   * (`quarentena_fila`, `lote.ler`) mas a RAZÃO da entrada é liberar
   * (`quarentena_liberar`, `lote.liberar`) — sem isto, Cleide veria "Quarentena"
   * no menu por ler, mesmo sem poder liberar nada lá dentro (AC-4).
   */
  requerTambemNoMenu?: ComponentId[]
}

export const ROTAS_OPERACAO: RotaOperacao[] = [
  {
    path: '/recebimento/novo',
    componente: 'recebimento_registrar',
    rotulo: 'Registrar recebimento',
    sub: 'leitor de código de barras',
    icone: Icone.Caixa,
    params: () => ({}),
  },
  {
    // Rótulo deliberadamente "Liberar quarentena", não "Quarentena": o MENU
    // (`PainelNavegacao.tsx`) já tem um indicador chamado "Quarentena"
    // (contagem, `estoque_indicador`) — dois itens com o mesmo texto ao lado
    // um do outro confundiriam qual é a fila de trabalho e qual é o número.
    path: '/quarentena',
    componente: 'quarentena_fila',
    rotulo: 'Liberar quarentena',
    sub: 'aguardando liberação do RT',
    icone: Icone.Caixa,
    params: () => ({}),
    requerTambemNoMenu: ['quarentena_liberar'],
  },
  {
    path: '/quarentena/:loteId',
    componente: 'quarentena_liberar',
    rotulo: 'Liberação de lote',
    sub: '',
    icone: Icone.Caixa,
    params: (p) => ({ lote_id: p.loteId ?? '' }),
  },
  {
    path: '/saida',
    componente: 'movimento_saida',
    rotulo: 'Saída',
    sub: 'separação com FEFO',
    icone: Icone.Seta,
    params: () => ({}),
  },
  {
    path: '/lotes',
    componente: 'lote_lista',
    rotulo: 'Lotes',
    sub: 'todo o estoque rastreável',
    icone: Icone.Lote,
    params: () => ({}),
  },
  {
    path: '/lotes/:id',
    componente: 'lote_detalhe',
    rotulo: 'Lote',
    sub: '',
    icone: Icone.Lote,
    params: (p) => ({ lote_id: p.id ?? '' }),
  },
  {
    path: '/vencimento',
    componente: 'fila_vencimento',
    rotulo: 'Vencimento',
    sub: 'o que vence em 90 dias',
    icone: Icone.Relogio,
    params: () => ({ janela: '90' }),
  },
  {
    path: '/controlados',
    componente: 'controlado_autorizar',
    rotulo: 'Controlados',
    sub: 'dupla identificação pendente',
    icone: Icone.Caixa,
    params: () => ({}),
  },
]

/** Subconjunto sem parâmetro na URL — o que entra na navegação lateral. As
 * rotas de detalhe (`:loteId`, `:id`) se chega por endereço, não por menu —
 * o mesmo tratamento que `/v/:viewId` já tem. */
export const NAV_ROTAS: readonly RotaOperacao[] = ROTAS_OPERACAO.filter((r) => !r.path.includes(':'))
