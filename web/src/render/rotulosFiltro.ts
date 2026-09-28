/**
 * Rótulos da barra de filtro (T-055). `Params` não carrega texto — um
 * `Literal["30","60","90"]` não sabe que "90" quer dizer "90 dias" — e o
 * contrato exportado também não (só o valor do enum, ver ADR-0011: prosa no
 * schema custa token de catálogo). Esta tabela é o único lugar com esse texto,
 * reaproveitando o que as views já têm em vez de duplicar.
 */
import { STATUS_LOTE, UNIDADE } from '../views/lote_lista'
import { STATUS_RECEBIMENTO } from '../views/recebimento_lista'
import { TIPO_MOVIMENTO } from '../views/movimento_lista'

/** `janela`, `horizonte`, `periodo` são todos "N dias, ou tudo" — o mesmo
 * vocabulário, três nomes de campo diferentes por causa de onde nasceram. */
function rotuloDias(valor: string): string {
  return valor === 'tudo' ? 'Tudo' : `${valor} dias`
}

const ROTULO_STATUS_MOVIMENTO: Record<string, string> = {
  efetivado: 'Efetivado',
  aguardando_autorizacao: 'Aguardando autorização',
  recusado: 'Recusado',
}

const ROTULO_ENTIDADE: Record<string, string> = {
  lote: 'Lote',
  movimento: 'Movimento',
  comando: 'Comando',
  recebimento: 'Recebimento',
  usuario: 'Usuário',
}

const ROTULO_METRICA: Record<string, string> = {
  quantidade: 'Quantidade',
  movimentos: 'Nº de movimentos',
  valor: 'Valor',
}

const ROTULO_TIPO_RELATORIO: Record<string, string> = {
  entrada: 'Entrada',
  saida: 'Saída',
  descarte: 'Descarte',
  estorno: 'Estorno',
  todos: 'Todos',
}

/** Nome do campo, como rótulo de controle na barra (`<label>`). */
const ROTULO_CAMPO: Record<string, string> = {
  unidade_id: 'Unidade',
  status: 'Situação',
  janela: 'Janela',
  periodo: 'Período',
  horizonte: 'Horizonte',
  tipo: 'Tipo',
  entidade: 'Entidade',
  metrica: 'Métrica',
}

export function rotuloCampo(campo: string): string {
  return ROTULO_CAMPO[campo] ?? campo
}

/** Valor do enum -> texto. Por campo, e por campo+componente quando o mesmo
 * nome de campo significa vocabulário diferente (`status`, `tipo`). `tipo` é
 * `string`, como em `BarraFiltro`: quem chama já confirmou que `FILTROS[tipo]`
 * existe, mas a checagem em si não estreita o literal. */
export function rotuloValor(tipo: string, campo: string, valor: string): string {
  if (campo === 'unidade_id') return UNIDADE[valor] ?? valor
  if (campo === 'janela' || campo === 'horizonte' || campo === 'periodo') return rotuloDias(valor)
  if (campo === 'entidade') return ROTULO_ENTIDADE[valor] ?? valor
  if (campo === 'metrica') return ROTULO_METRICA[valor] ?? valor
  if (campo === 'status') {
    if (tipo === 'lote_lista') return STATUS_LOTE[valor as keyof typeof STATUS_LOTE]?.rotulo ?? valor
    if (tipo === 'recebimento_lista') {
      return STATUS_RECEBIMENTO[valor as keyof typeof STATUS_RECEBIMENTO]?.rotulo ?? valor
    }
    if (tipo === 'movimento_lista') return ROTULO_STATUS_MOVIMENTO[valor] ?? valor
  }
  if (campo === 'tipo' && tipo === 'movimento_lista') {
    return TIPO_MOVIMENTO[valor as keyof typeof TIPO_MOVIMENTO]?.rotulo ?? valor
  }
  if (campo === 'tipo' && tipo === 'relatorio_movimentacao') return ROTULO_TIPO_RELATORIO[valor] ?? valor
  return valor
}
