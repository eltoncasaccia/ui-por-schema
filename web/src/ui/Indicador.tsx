import { BarraFaixas, type Faixa } from './BarraFaixas'
import type { Tom } from './estados'

/**
 * Um número COM contexto.
 *
 * Um número sozinho é uma métrica sem contexto: "3" não diz de onde, não diz se
 * é muito, e não diz o que fazer. Este componente responde a pergunta seguinte
 * antes de ela ser feita — o escopo, a decomposição, e o que exige ação.
 */
export function Indicador({
  rotulo, valor, escopo, detalhe, faixas, tipoFaixa = 'nenhum', tom = 'neutro',
}: {
  rotulo: string
  valor: string
  escopo?: string | undefined
  detalhe?: string | undefined
  faixas?: Faixa[] | undefined
  tipoFaixa?: 'urgencia' | 'unidade' | 'nenhum'
  tom?: Tom
}) {
  return (
    <section className={`indicador tom-${tom}`}>
      <div className="indicador-rotulo">{rotulo}</div>
      <div className="indicador-valor">{valor}</div>
      {escopo && <div className="indicador-nota">em {escopo}</div>}
      {faixas && faixas.length > 0 && tipoFaixa !== 'nenhum' && (
        <BarraFaixas faixas={faixas} tipo={tipoFaixa} />
      )}
      {detalhe && (
        <p className="indicador-detalhe">{detalhe}</p>
      )}
    </section>
  )
}
