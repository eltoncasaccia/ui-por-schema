/* GERADO por `make types` — NÃO EDITE.
 *
 * Vem do registry da API (`estoque.registry.exportar`). Editar aqui faz o
 * arquivo divergir da fonte, e a divergência só aparece quando alguém
 * confia no tipo errado. Para mudar, mude o componente na API.
 */

/**
 * Sem custo, para papel nenhum (CA-05) — inclusive em `valor_novo`.
 */
export interface VMAuditoriaTrilha {
  linhas: AuditoriaTrilhaLinhaTrilha[]
  recorte: string
  total: number
  truncada: boolean
}
export interface AuditoriaTrilhaLinhaTrilha {
  acao: string
  ator: string | null
  criado_em: string
  entidade: string | null
  entidade_id: string | null
  filtrada?: boolean
  id: number
  origem: string
  valor_anterior: {
    [k: string]: unknown
  } | null
  valor_novo: {
    [k: string]: unknown
  } | null
}

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
export interface VMMovimentoLista {
  escopo: string
  linhas: MovimentoListaLinhaMovimento[]
  pendentes: number
  recorte: string
  total: number
}
export interface MovimentoListaLinhaMovimento {
  autor: string
  autorizador: string | null
  complemento: string | null
  criado_em: string
  estorna: string | null
  estornado_por: string | null
  lote_id: string
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
  parado_ha_dias?: number | null
  quantidade: number
  status: 'efetivado' | 'aguardando_autorizacao' | 'recusado'
  status_rotulo: string
  tipo: 'entrada' | 'saida' | 'descarte' | 'estorno'
  unidade: string
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
 * E' EXATAMENTE isto que atravessa a rede.
 *
 * `custo_unitario_centavos` so' aparece quando pedido E permitido — nos demais
 * casos a chave fica AUSENTE (CA-05, AC-1), nunca `null`: `null` ainda
 * revelaria que o campo existe.
 */
export interface VMProdutoFicha {
  ativo: boolean
  classe: 'comum' | 'controlado' | 'termolabil' | 'antimicrobiano'
  curva_abc: 'A' | 'B' | 'C'
  custo_unitario_centavos?: number | null
  ean: string
  fabricante: string
  nome: string
  principio_ativo: string
  produto_id: string
  saldo_total: number
}

export interface VMProdutoSaldoPorUnidade {
  ativo: boolean
  linhas: ProdutoSaldoPorUnidadeLinhaUnidade[]
  nome: string
  produto_id: string
  total: number
}
export interface ProdutoSaldoPorUnidadeLinhaUnidade {
  lotes: number
  saldo: number
  unidade: string
  unidade_id: string
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

/**
 * Sem custo nem margem (CA-05): `Movimento` nao os carrega, e nada aqui os
 * busca. So' uma das duas listas vem preenchida, conforme `direcao`.
 */
export interface VMRastreabilidade {
  alvo: string
  clientes?: RastreabilidadeSaidaParaCliente[]
  direcao: 'lote_para_clientes' | 'cliente_para_lotes'
  lotes?: RastreabilidadeLoteDeCliente[]
  recorte: string
  total_quantidade: number
  total_saidas: number
}
export interface RastreabilidadeSaidaParaCliente {
  cliente: string
  data: string
  nota_fiscal: string | null
  quantidade: number
}
export interface RastreabilidadeLoteDeCliente {
  lote_id: string
  numero: string
  primeira: string
  produto: string
  quantidade_total: number
  ultima: string
}

/**
 * Sem custo, para papel nenhum (CA-05). `Recebimento` nao carrega custo e
 * nada aqui o busca.
 */
export interface VMRecebimentoDetalhe {
  conferente: string
  fornecedor: string
  nota_fiscal: string
  recebido_em: string
  recebimento_id: string
  responsavel_tecnico: string | null
  status: 'rascunho' | 'conferido' | 'liberado'
  status_rotulo: string
  tem_pendencia_divergencia: boolean
  temperatura_chegada_c: number | null
  unidade: string
}

/**
 * Sem custo, para papel nenhum (CA-05, ADR-0020). `Recebimento` nao carrega
 * custo e nada aqui o busca — o AC-7 e' verdadeiro por construcao, e testado.
 */
export interface VMRecebimentoLista {
  com_divergencia: number
  escopo: string
  linhas: RecebimentoListaLinhaRecebimento[]
  recorte: string
  total: number
}
export interface RecebimentoListaLinhaRecebimento {
  divergencia: boolean
  fornecedor: string
  nota_fiscal: string
  recebido_em: string
  recebimento_id: string
  status: 'rascunho' | 'conferido' | 'liberado'
  status_rotulo: string
  unidade: string
}

/**
 * Sem custo, para papel nenhum (CA-05, ADR-0020).
 *
 * `Produto` carrega custo para quem tem `custo.ler`, e `ProdutoLido` não o
 * declara — o que não entra no viewmodel não chega ao navegador.
 */
export interface VMRecebimentoRegistrar {
  ean_nao_encontrado?: string | null
  lido?: RecebimentoRegistrarProdutoLido | null
  obrigatorios_do_item: string[]
  unidade_sugerida: string | null
  unidades: RecebimentoRegistrarUnidadeDestino[]
  validade_minima_dias: number
}
/**
 * O que o leitor resolveu, já com o que a classe do produto exige.
 *
 * `exige_temperatura` e `exige_rt` são calculados **no servidor**, a partir da
 * classe. Se fossem decididos no cliente, um formulário adulterado marcaria o
 * termolábil como dispensando temperatura — e a interface é payload
 * não-confiável como qualquer outro (ADR-0004). A recusa real acontece no
 * comando de qualquer forma; isto aqui é para a tela não pedir errado.
 */
export interface RecebimentoRegistrarProdutoLido {
  classe: 'comum' | 'controlado' | 'termolabil' | 'antimicrobiano'
  ean: string
  exige_rt: boolean
  exige_temperatura: boolean
  fabricante: string
  nome: string
  produto_id: string
}
export interface RecebimentoRegistrarUnidadeDestino {
  id: string
  nome: string
}

/**
 * Sem custo (CA-05): nada aqui busca produto por preco, so' por nome.
 */
export interface VMTemperaturaExcursoes {
  ate: string
  de: string
  excursoes: TemperaturaExcursoesExcursao[]
  faixa_max_c?: number
  faixa_min_c?: number
  total_excursoes: number
  unidade: string
}
export interface TemperaturaExcursoesExcursao {
  duracao_horas: number
  fim: string
  inicio: string
  leituras: number
  lotes: TemperaturaExcursoesLotePresente[]
  pico_celsius: number
  sentido: 'calor' | 'frio'
}
export interface TemperaturaExcursoesLotePresente {
  entrou_em: string
  lote_id: string
  numero: string
  produto: string
  status: 'quarentena' | 'liberado' | 'bloqueado' | 'descartado'
}

/**
 * Sem custo (CA-05): temperatura nao tem preco, e nada aqui busca produto.
 *
 * `pontos` **ou** `baldes` vem preenchido, nunca os dois — `agregado` diz qual.
 * `csv` e' a exportacao (AC-2), montada das mesmas linhas.
 */
export interface VMTemperaturaHistorico {
  agregado: boolean
  ate: string
  baldes?: TemperaturaHistoricoBalde[]
  csv: string
  de: string
  exportavel?: boolean
  faixa_max_c?: number
  faixa_min_c?: number
  leituras_fora_da_faixa: number
  pontos?: TemperaturaHistoricoPonto[]
  total_leituras: number
  unidade: string
}
/**
 * Um intervalo agregado. `tem_excursao` marca o balde que esconde ao menos
 * uma leitura fora da faixa — sem ele, agregar apagaria a excursao.
 */
export interface TemperaturaHistoricoBalde {
  fim: string
  inicio: string
  leituras: number
  maximo: number
  media: number
  minimo: number
  tem_excursao: boolean
}
export interface TemperaturaHistoricoPonto {
  celsius: number
  fora_da_faixa: boolean
  instante: string
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
  | 'auditoria_trilha'
  | 'controlado_autorizar'
  | 'estoque_indicador'
  | 'fila_vencimento'
  | 'lote_detalhe'
  | 'lote_lista'
  | 'lote_movimentos'
  | 'lote_status_acao'
  | 'movimento_lista'
  | 'movimento_saida'
  | 'produto_ficha'
  | 'produto_saldo_por_unidade'
  | 'quarentena_fila'
  | 'quarentena_liberar'
  | 'rastreabilidade'
  | 'recebimento_detalhe'
  | 'recebimento_lista'
  | 'recebimento_registrar'
  | 'temperatura_excursoes'
  | 'temperatura_historico'
  | 'vencimento_grafico'

/** Usado pelo teste de bijeção: toda view precisa corresponder a um destes. */
export const IDS_DA_API: readonly ComponentId[] = [
  'auditoria_trilha',
  'controlado_autorizar',
  'estoque_indicador',
  'fila_vencimento',
  'lote_detalhe',
  'lote_lista',
  'lote_movimentos',
  'lote_status_acao',
  'movimento_lista',
  'movimento_saida',
  'produto_ficha',
  'produto_saldo_por_unidade',
  'quarentena_fila',
  'quarentena_liberar',
  'rastreabilidade',
  'recebimento_detalhe',
  'recebimento_lista',
  'recebimento_registrar',
  'temperatura_excursoes',
  'temperatura_historico',
  'vencimento_grafico',
] as const

/** O viewmodel de cada componente — o que de fato atravessa a rede. */
export interface ViewModels {
  auditoria_trilha: VMAuditoriaTrilha
  controlado_autorizar: VMControladoAutorizar
  estoque_indicador: VMEstoqueIndicador
  fila_vencimento: VMFilaVencimento
  lote_detalhe: VMLoteDetalhe
  lote_lista: VMLoteLista
  lote_movimentos: VMLoteMovimentos
  lote_status_acao: VMLoteStatusAcao
  movimento_lista: VMMovimentoLista
  movimento_saida: VMMovimentoSaida
  produto_ficha: VMProdutoFicha
  produto_saldo_por_unidade: VMProdutoSaldoPorUnidade
  quarentena_fila: VMQuarentenaFila
  quarentena_liberar: VMQuarentenaLiberar
  rastreabilidade: VMRastreabilidade
  recebimento_detalhe: VMRecebimentoDetalhe
  recebimento_lista: VMRecebimentoLista
  recebimento_registrar: VMRecebimentoRegistrar
  temperatura_excursoes: VMTemperaturaExcursoes
  temperatura_historico: VMTemperaturaHistorico
  vencimento_grafico: VMVencimentoGrafico
}

export type ViewModel<Id extends ComponentId> = ViewModels[Id]

/** O layout obedece ao componente, nunca ao modelo. */
export const TAMANHOS: Record<ComponentId, string> = {
  auditoria_trilha: 'inteira',
  controlado_autorizar: 'inteira',
  estoque_indicador: 'linha',
  fila_vencimento: 'inteira',
  lote_detalhe: 'meia',
  lote_lista: 'inteira',
  lote_movimentos: 'inteira',
  lote_status_acao: 'inteira',
  movimento_lista: 'inteira',
  movimento_saida: 'inteira',
  produto_ficha: 'meia',
  produto_saldo_por_unidade: 'meia',
  quarentena_fila: 'inteira',
  quarentena_liberar: 'inteira',
  rastreabilidade: 'inteira',
  recebimento_detalhe: 'inteira',
  recebimento_lista: 'inteira',
  recebimento_registrar: 'inteira',
  temperatura_excursoes: 'inteira',
  temperatura_historico: 'alta',
  vencimento_grafico: 'inteira',
}
