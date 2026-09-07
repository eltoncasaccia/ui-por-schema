import { useEstreito } from './useEstreito'
import { Etiqueta } from './Etiqueta'
import { classeTexto, type Tom } from './estados'

export interface Coluna<T> {
  chave: string
  rotulo: string
  num?: boolean
  /** No modo cartão, campos marcados aparecem como par rótulo/valor. */
  campo?: boolean
  render: (linha: T) => React.ReactNode
}

/**
 * Tabela que NÃO quebra: em coluna estreita vira lista de cartões.
 *
 * Rolagem horizontal esconde coluna, e coluna escondida numa tabela de lotes
 * é um dado regulatório que sumiu. Cartão mostra tudo.
 */
export function Tabela<T>({
  colunas, linhas, chave, titulo, etiqueta,
}: {
  colunas: Coluna<T>[]
  linhas: T[]
  chave: (l: T) => string
  /** Primeira coluna vira o título do cartão. */
  titulo: (l: T) => React.ReactNode
  etiqueta?: (l: T) => { texto: string; tom: Tom } | null
}) {
  const [ref, estreito] = useEstreito()

  if (linhas.length === 0) {
    return <div ref={ref}><p className="vazio">Nada aqui.</p></div>
  }

  if (estreito) {
    return (
      <div ref={ref} className="lista-cartoes">
        {linhas.map((l) => {
          const e = etiqueta?.(l)
          return (
            <article key={chave(l)} className="linha-cartao">
              <div className="linha-cartao-topo">
                <div style={{ minWidth: 0 }}>{titulo(l)}</div>
                {e && <Etiqueta tom={e.tom}>{e.texto}</Etiqueta>}
              </div>
              <div className="linha-cartao-campos">
                {colunas.filter((c) => c.campo).map((c) => (
                  <div key={c.chave}>
                    <div className="campo-rotulo">{c.rotulo}</div>
                    <div className="campo-valor">{c.render(l)}</div>
                  </div>
                ))}
              </div>
            </article>
          )
        })}
      </div>
    )
  }

  return (
    <div ref={ref} className="tabela-rolagem">
      <table className="tabela">
        <thead>
          <tr>
            {colunas.map((c) => (
              <th key={c.chave} className={c.num ? 'num' : undefined}>{c.rotulo}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {linhas.map((l) => (
            <tr key={chave(l)}>
              {colunas.map((c) => (
                <td key={c.chave} className={c.num ? 'num' : undefined}>{c.render(l)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export { classeTexto }
