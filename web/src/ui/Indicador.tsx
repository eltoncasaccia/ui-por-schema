import type { Tom } from './estados'

/**
 * Um número, um rótulo, um estado.
 *
 * O rótulo usa `overflow-wrap: anywhere` e o valor usa `clamp()` — foi o que
 * quebrava quando o mesmo componente era renderizado na coluna estreita do
 * assistente e na coluna larga do workspace.
 */
export function Indicador({
  rotulo, valor, nota, tom = 'neutro',
}: { rotulo: string; valor: string; nota?: string | undefined; tom?: Tom }) {
  return (
    <div className={`indicador tom-${tom}`}>
      <div className="indicador-rotulo">{rotulo}</div>
      <div className="indicador-valor">{valor}</div>
      {nota && <div className="indicador-nota">{nota}</div>}
    </div>
  )
}
