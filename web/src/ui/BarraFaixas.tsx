/**
 * Distribuição por faixa de urgência, numa barra segmentada.
 *
 * Por que ESTA forma: a pergunta é composição-dentro-de-um-total ("dos 12 que
 * vencem, quantos são graves?"). Uma barra segmentada responde composição e
 * total de uma vez, cabe numa linha e não compete com o número principal.
 *
 * Por que UMA matiz: urgência é MAGNITUDE, não identidade. Rampa sequencial
 * separa por luminosidade, que toda forma de daltonismo preserva. Duas matizes
 * (âmbar/laranja) foram testadas e reprovadas — ΔE 0.4 para deuteranopia no
 * tema claro, ou seja, indistinguíveis.
 *
 * Rótulo direto em cada segmento: é o alívio exigido quando um degrau claro da
 * rampa não alcança 3:1 contra a superfície branca.
 */
/**
 * Forma MÍNIMA que a barra precisa.
 *
 * `ordem` é opcional porque no viewmodel gerado ela tem default — foi o
 * primeiro desencontro que o codegen pegou: aqui estava obrigatória, e o tipo
 * escrito à mão aceitava o que a API não garante.
 */
export interface Faixa { rotulo: string; valor: number; ordem?: number }

export function BarraFaixas({
  faixas, tipo,
}: { faixas: Faixa[] | undefined; tipo: 'urgencia' | 'unidade' }) {
  // Campo com default no Pydantic chega opcional no tipo gerado. Tratar aqui,
  // uma vez, evita `?? []` espalhado por cada view que usa a barra.
  const lista = faixas ?? []
  const total = lista.reduce((s, f) => s + f.valor, 0)
  if (total === 0) return null

  return (
    <div className="faixas">
      <div className="faixas-barra" role="img"
        aria-label={lista.map((f) => `${f.rotulo}: ${f.valor}`).join('; ')}>
        {lista.map((f) => (
          <span
            key={f.rotulo}
            className={tipo === 'urgencia' ? `seg seg-u${f.ordem ?? 0}` : 'seg seg-neutro'}
            style={{ flexGrow: f.valor }}
            title={`${f.rotulo}: ${f.valor}`}
          />
        ))}
      </div>
      <ul className="faixas-legenda">
        {lista.map((f) => (
          <li key={f.rotulo}>
            <span className={tipo === 'urgencia' ? `ponto seg-u${f.ordem ?? 0}` : 'ponto seg-neutro'} />
            {/* identidade nunca por cor sozinha: rótulo sempre junto */}
            <span className="faixas-rotulo">{f.rotulo}</span>
            <span className="faixas-valor">{f.valor}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
