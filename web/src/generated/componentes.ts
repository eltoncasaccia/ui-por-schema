/* GERADO por `make types` — NÃO EDITE.
 *
 * Vem do registry da API (`estoque.registry.exportar`). Editar aqui faz o
 * arquivo divergir da fonte, e a divergência só aparece quando alguém
 * confia no tipo errado. Para mudar, mude o componente na API.
 */

/**
 * Sem custo, para papel nenhum (CA-05, ADR-0020).
 */
export interface VMControladoAutorizar {
  alvo?: ControladoAutorizarPendente | null
  escopo: string
  fila?: ControladoAutorizarPendente[]
  motivo_impedimento?: string | null
  pode_decidir?: boolean
  total: number
}
export interface ControladoAutorizarPendente {
  autor: string
  lote_id: string
  motivo: string
  movimento_id: string
  parado_ha_dias: number
  produto: string
  quantidade: number
  submetido_em: string
  unidade: string
}

export interface VMEstoqueIndicador {
  detalhe?: string | null
  escopo: string
  faixas?: EstoqueIndicadorFaixa[]
  metrica: 'lotes_em_quarentena' | 'lotes_vencendo_90d' | 'lotes_bloqueados' | 'valor_em_estoque'
  rotulo: string
  tipo_faixa?: 'urgencia' | 'unidade' | 'nenhum'
  unidade_medida: 'lotes' | 'centavos'
  valor: number
}
/**
 * Um pedaco da decomposicao. `ordem` posiciona na rampa sequencial.
 */
export interface EstoqueIndicadorFaixa {
  ordem?: number
  rotulo: string
  valor: number
}

/**
 * O viewmodel. E' EXATAMENTE isto que atravessa a rede — nada de `Lote`,
 * nada de linha de banco, nada de custo (ADR-0020, CA-05).
 */
export interface VMFilaVencimento {
  cursor?: string | null
  janela_dias: number
  linhas: FilaVencimentoLinhaVencimento[]
  resumo?: FilaVencimentoFaixaResumo[]
  tem_mais?: boolean
  total: number
}
export interface FilaVencimentoLinhaVencimento {
  dias_restantes: number
  lote_id: string
  numero: string
  produto: string
  saldo: number
  situacao: 'ok' | 'alerta_90' | 'bloqueio_30' | 'vencido'
  unidade: string
  validade: string
}
/**
 * Uma faixa da rampa de urgencia. `ordem` cresce com a urgencia.
 */
export interface FilaVencimentoFaixaResumo {
  ordem: number
  rotulo: string
  valor: number
}

/**
 * Sem custo, para papel nenhum (CA-05). O custo unitario e' de
 * `produto_ficha`; nao esta' aqui, entao nao atravessa a rede (ADR-0020).
 */
export interface VMLoteDetalhe {
  classe: 'comum' | 'controlado' | 'termolabil' | 'antimicrobiano'
  dias_restantes: number
  endereco: string | null
  fabricacao: string
  lote_id: string
  numero: string
  produto: string
  saldo: number
  situacao: 'ok' | 'alerta_90' | 'bloqueio_30' | 'vencido'
  status_efetivo: 'quarentena' | 'liberado' | 'bloqueado' | 'descartado' | 'vencido' | 'esgotado'
  status_registrado: 'quarentena' | 'liberado' | 'bloqueado' | 'descartado'
  unidade: string
  validade: string
}

/**
 * O que atravessa a rede. Sem custo, para papel nenhum (CA-05, ADR-0020):
 * custo e' de `produto_ficha`, e o que nao esta' aqui nao chega ao navegador.
 */
export interface VMLoteLista {
  cursor?: string | null
  escopo: string
  linhas: LoteListaLinhaLote[]
  recorte?: string[]
  resumo?: LoteListaFaixa[]
  tem_mais?: boolean
  total: number
}
export interface LoteListaLinhaLote {
  dias_restantes: number
  endereco: string | null
  fabricacao: string
  lote_id: string
  numero: string
  produto: string
  saldo: number
  situacao: 'ok' | 'alerta_90' | 'bloqueio_30' | 'vencido'
  status: 'quarentena' | 'liberado' | 'bloqueado' | 'descartado' | 'vencido' | 'esgotado'
  unidade: string
  validade: string
}
export interface LoteListaFaixa {
  ordem?: number
  rotulo: string
  valor: number
}

/**
 * Sem custo, para papel nenhum (CA-05): o extrato responde quanto entrou e
 * quanto saiu, nunca quanto vale (ADR-0020).
 */
export interface VMLoteMovimentos {
  cursor?: string | null
  linhas: LoteMovimentosLinhaMovimento[]
  lote_id: string
  numero: string
  periodo_dias: number | null
  produto: string
  saldo_atual: number
  tem_mais?: boolean
  total: number
  unidade: string
}
export interface LoteMovimentosLinhaMovimento {
  autor_id: string
  autorizador_id: string | null
  complemento: string | null
  criado_em: string
  estorna_movimento_id: string | null
  motivo:
    | 'recebimento'
    | 'venda'
    | 'transferencia'
    | 'avaria'
    | 'furto'
    | 'erro_de_separacao'
    | 'erro_de_recebimento'
    | 'vencimento'
    | 'erro_de_contagem_anterior'
    | 'estorno'
  movimento_id: string
  quantidade: number
  saldo_apos: number
  status: 'efetivado' | 'aguardando_autorizacao' | 'recusado'
  tipo: 'entrada' | 'saida' | 'descarte' | 'estorno'
}

/**
 * Sem custo, para papel nenhum (CA-05, ADR-0020).
 */
export interface VMLoteStatusAcao {
  acoes: LoteStatusAcaoAcaoDisponivel[]
  dias_restantes: number
  lote_id: string
  numero: string
  produto: string
  saldo: number
  situacao: 'ok' | 'alerta_90' | 'bloqueio_30' | 'vencido'
  status: 'quarentena' | 'liberado' | 'bloqueado' | 'descartado'
  status_efetivo: 'quarentena' | 'liberado' | 'bloqueado' | 'descartado' | 'vencido' | 'esgotado'
  unidade: string
  validade: string
}
/**
 * Uma linha da tabela §4.1, já avaliada contra este lote.
 *
 * `motivo` é preenchido quando a ação não cabe. Dizer *por que* não cabe é o
 * que impede a leitura errada de que o sistema está quebrado — e o texto fala
 * do estado do lote, nunca de quem poderia fazer.
 */
export interface LoteStatusAcaoAcaoDisponivel {
  acao: 'bloquear' | 'desbloquear' | 'liberar_vencimento'
  disponivel: boolean
  motivo?: string | null
  rotulo: string
}

/**
 * Sem custo, para papel nenhum (CA-05, ADR-0020).
 */
export interface VMMovimentoSaida {
  alternativas?: MovimentoSaidaLoteCandidato[]
  classe: 'comum' | 'controlado' | 'termolabil' | 'antimicrobiano'
  escopo: string
  exige_autorizacao: boolean
  motivos: MovimentoSaidaOpcaoMotivo[]
  produto: string
  proposta?: MovimentoSaidaLoteCandidato | null
  sem_estoque?: boolean
}
export interface MovimentoSaidaLoteCandidato {
  dias_restantes: number
  disponivel: boolean
  exige_liberacao_rt?: boolean
  lote_id: string
  motivo?: string | null
  numero: string
  proposto: boolean
  saldo: number
  situacao: 'ok' | 'alerta_90' | 'bloqueio_30' | 'vencido'
  status_efetivo: 'quarentena' | 'liberado' | 'bloqueado' | 'descartado' | 'vencido' | 'esgotado'
  unidade: string
  validade: string
}
export interface MovimentoSaidaOpcaoMotivo {
  exige_destinatario: boolean
  rotulo: string
  valor: 'venda' | 'avaria' | 'furto' | 'erro_de_separacao'
}

/**
 * Sem custo, para papel nenhum (CA-05, ADR-0020).
 */
export interface VMQuarentenaFila {
  cursor?: string | null
  escopo: string
  linhas: QuarentenaFilaLinhaQuarentena[]
  resumo?: QuarentenaFilaFaixa[]
  tem_mais?: boolean
  total: number
  vencidos: number
}
export interface QuarentenaFilaLinhaQuarentena {
  classe: 'comum' | 'controlado' | 'termolabil' | 'antimicrobiano'
  dias_restantes: number
  fabricacao: string
  fabricado_ha_dias: number
  lote_id: string
  numero: string
  produto: string
  saldo: number
  situacao: 'ok' | 'alerta_90' | 'bloqueio_30' | 'vencido'
  status_efetivo: 'quarentena' | 'liberado' | 'bloqueado' | 'descartado' | 'vencido' | 'esgotado'
  unidade: string
  validade: string
}
export interface QuarentenaFilaFaixa {
  ordem?: number
  rotulo: string
  valor: number
}

/**
 * Sem custo, para papel nenhum (CA-05, ADR-0020).
 */
export interface VMQuarentenaLiberar {
  aviso_validade?: string | null
  classe: 'comum' | 'controlado' | 'termolabil' | 'antimicrobiano'
  conferencia: QuarentenaLiberarItemConferencia[]
  dias_restantes: number
  fabricacao: string
  lote_id: string
  motivo?: string | null
  numero: string
  pode_decidir: boolean
  produto: string
  saldo: number
  situacao: 'ok' | 'alerta_90' | 'bloqueio_30' | 'vencido'
  status: 'quarentena' | 'liberado' | 'bloqueado' | 'descartado'
  status_efetivo: 'quarentena' | 'liberado' | 'bloqueado' | 'descartado' | 'vencido' | 'esgotado'
  unidade: string
  validade: string
}
/**
 * Um item do checklist de `RN-R03`.
 *
 * `obrigatorio` é calculado no servidor, a partir da classe do produto. Se
 * fosse decidido no cliente, um formulário adulterado marcaria a temperatura
 * como dispensável e o termolábil passaria sem conferência — e a interface é
 * payload não-confiável como qualquer outro (ADR-0004).
 */
export interface QuarentenaLiberarItemConferencia {
  campo: string
  obrigatorio: boolean
  rotulo: string
}

export interface VMVencimentoGrafico {
  baldes: VencimentoGraficoBalde[]
  escopo: string
  horizonte_dias: number
  legenda: string[]
  pico_rotulo: string | null
  total_lotes: number
}
/**
 * Uma barra. `urgencia` posiciona na rampa: 0 tranquilo, 3 vencido.
 */
export interface VencimentoGraficoBalde {
  inicio: string
  lotes: number
  rotulo: string
  unidades: number
  urgencia: number
}

/** Os ids que a API registra. O cliente não inventa id. */
export type ComponentId =
  | 'controlado_autorizar'
  | 'estoque_indicador'
  | 'fila_vencimento'
  | 'lote_detalhe'
  | 'lote_lista'
  | 'lote_movimentos'
  | 'lote_status_acao'
  | 'movimento_saida'
  | 'quarentena_fila'
  | 'quarentena_liberar'
  | 'vencimento_grafico'

/** Usado pelo teste de bijeção: toda view precisa corresponder a um destes. */
export const IDS_DA_API: readonly ComponentId[] = [
  'controlado_autorizar',
  'estoque_indicador',
  'fila_vencimento',
  'lote_detalhe',
  'lote_lista',
  'lote_movimentos',
  'lote_status_acao',
  'movimento_saida',
  'quarentena_fila',
  'quarentena_liberar',
  'vencimento_grafico',
] as const

/** O viewmodel de cada componente — o que de fato atravessa a rede. */
export interface ViewModels {
  controlado_autorizar: VMControladoAutorizar
  estoque_indicador: VMEstoqueIndicador
  fila_vencimento: VMFilaVencimento
  lote_detalhe: VMLoteDetalhe
  lote_lista: VMLoteLista
  lote_movimentos: VMLoteMovimentos
  lote_status_acao: VMLoteStatusAcao
  movimento_saida: VMMovimentoSaida
  quarentena_fila: VMQuarentenaFila
  quarentena_liberar: VMQuarentenaLiberar
  vencimento_grafico: VMVencimentoGrafico
}

export type ViewModel<Id extends ComponentId> = ViewModels[Id]

/** O layout obedece ao componente, nunca ao modelo. */
export const TAMANHOS: Record<ComponentId, string> = {
  controlado_autorizar: 'inteira',
  estoque_indicador: 'linha',
  fila_vencimento: 'inteira',
  lote_detalhe: 'meia',
  lote_lista: 'inteira',
  lote_movimentos: 'inteira',
  lote_status_acao: 'inteira',
  movimento_saida: 'inteira',
  quarentena_fila: 'inteira',
  quarentena_liberar: 'inteira',
  vencimento_grafico: 'inteira',
}
