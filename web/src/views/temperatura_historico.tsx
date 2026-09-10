import { Etiqueta } from '../ui/Etiqueta'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'
import { UNIDADE } from './lote_lista'

type VM = ViewModel<'temperatura_historico'>
type Ponto = NonNullable<VM['pontos']>[number]
type Balde = NonNullable<VM['baldes']>[number]

function dataBr(iso: string): string {
  return new Date(iso).toLocaleDateString('pt-BR')
}

/** Download client-side: os dados são exatamente os do `vm` — nada é rebuscado. */
function baixarCsv(nome: string, conteudo: string): void {
  const url = URL.createObjectURL(new Blob([conteudo], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = nome
  a.click()
  URL.revokeObjectURL(url)
}

/**
 * O gráfico é uma faixa 2–8 °C sombreada com a série por cima. Quando o período
 * é longo o servidor já agregou em baldes (min–máx–média); o desenho usa a
 * banda min–máx e a linha da média. A pergunta é "a temperatura ficou na faixa,
 * e quando não ficou?" — por isso a faixa útil é o fundo, não uma linha a mais.
 */
function Grafico({ vm }: { vm: VM }) {
  const L = 640
  const A = 160
  const tMin = Math.min(vm.faixa_min_c ?? 2, ...serieMin(vm)) - 1
  const tMax = Math.max(vm.faixa_max_c ?? 8, ...serieMax(vm)) + 1
  const y = (c: number) => A - ((c - tMin) / (tMax - tMin)) * A
  const n = (vm.agregado ? vm.baldes?.length : vm.pontos?.length) ?? 0
  const x = (i: number) => (n <= 1 ? L / 2 : (i / (n - 1)) * L)

  const faixaTopo = y(vm.faixa_max_c ?? 8)
  const faixaBase = y(vm.faixa_min_c ?? 2)

  return (
    <svg
      viewBox={`0 0 ${L} ${A}`}
      preserveAspectRatio="none"
      role="img"
      aria-label={`Temperatura de ${dataBr(vm.de)} a ${dataBr(vm.ate)}: ${
        vm.leituras_fora_da_faixa === 0
          ? 'sempre dentro da faixa de 2 a 8 graus'
          : `${vm.leituras_fora_da_faixa} leituras fora da faixa`
      }`}
      style={{ width: '100%', height: A, display: 'block', overflow: 'visible' }}
    >
      <rect
        x={0}
        y={faixaTopo}
        width={L}
        height={faixaBase - faixaTopo}
        fill="var(--bom-b)"
        opacity={0.5}
      />
      <line x1={0} y1={faixaTopo} x2={L} y2={faixaTopo} stroke="var(--bom)" strokeWidth={1} />
      <line x1={0} y1={faixaBase} x2={L} y2={faixaBase} stroke="var(--bom)" strokeWidth={1} />

      {vm.agregado && vm.baldes
        ? faixaBaldes(vm.baldes, x, y)
        : linhaPontos(vm.pontos ?? [], x, y)}
    </svg>
  )
}

function serieMin(vm: VM): number[] {
  if (vm.agregado) return (vm.baldes ?? []).map((b) => b.minimo)
  return (vm.pontos ?? []).map((p) => p.celsius)
}
function serieMax(vm: VM): number[] {
  if (vm.agregado) return (vm.baldes ?? []).map((b) => b.maximo)
  return (vm.pontos ?? []).map((p) => p.celsius)
}

function linhaPontos(pontos: Ponto[], x: (i: number) => number, y: (c: number) => number) {
  if (pontos.length === 0) return null
  const d = pontos.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(p.celsius)}`).join(' ')
  return (
    <>
      <path d={d} fill="none" stroke="var(--texto)" strokeWidth={1.5} />
      {pontos.map((p, i) =>
        p.fora_da_faixa ? (
          <circle key={i} cx={x(i)} cy={y(p.celsius)} r={3} fill="var(--laranja)" />
        ) : null,
      )}
    </>
  )
}

function faixaBaldes(baldes: Balde[], x: (i: number) => number, y: (c: number) => number) {
  const cima = baldes.map((b, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(b.maximo)}`).join(' ')
  const baixo = baldes
    .map((b, i) => ({ b, i }))
    .reverse()
    .map(({ b, i }) => `L ${x(i)} ${y(b.minimo)}`)
    .join(' ')
  const media = baldes.map((b, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(b.media)}`).join(' ')
  return (
    <>
      <path d={`${cima} ${baixo} Z`} fill="var(--dim)" opacity={0.25} stroke="none" />
      <path d={media} fill="none" stroke="var(--texto)" strokeWidth={1.5} />
      {baldes.map((b, i) =>
        b.tem_excursao ? (
          <circle key={i} cx={x(i)} cy={y(b.maximo)} r={3} fill="var(--laranja)" />
        ) : null,
      )}
    </>
  )
}

export const view: View<'temperatura_historico'> = ({ vm }) => {
  const foraDaFaixa = vm.leituras_fora_da_faixa > 0
  return (
    <section className="cartao">
      <div className="cartao-cabeca">
        <span className="titulo-painel">Temperatura · {UNIDADE[vm.unidade] ?? vm.unidade}</span>
        <span className="mono fraco" style={{ fontSize: 11 }}>
          {dataBr(vm.de)} — {dataBr(vm.ate)}
        </span>
      </div>

      <div className="cartao-corpo">
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'baseline', marginBottom: 8 }}>
          <span className="suave" style={{ fontSize: 13 }}>
            {vm.total_leituras.toLocaleString('pt-BR')} leitura{vm.total_leituras === 1 ? '' : 's'}
            {vm.agregado && ' · agregadas por intervalo'}
          </span>
          {foraDaFaixa ? (
            <Etiqueta tom="laranja">
              {vm.leituras_fora_da_faixa} fora da faixa 2–8 °C
            </Etiqueta>
          ) : (
            <Etiqueta tom="bom">sempre dentro de 2–8 °C</Etiqueta>
          )}
        </div>

        {vm.total_leituras === 0 ? (
          <p className="vazio">Sem leitura de temperatura neste período.</p>
        ) : (
          <Grafico vm={vm} />
        )}

        <div style={{ marginTop: 12 }}>
          <button
            type="button"
            className="btn"
            onClick={() => baixarCsv(`temperatura-${vm.unidade}-${vm.de}-a-${vm.ate}.csv`, vm.csv)}
          >
            Baixar CSV
          </button>
        </div>
      </div>
    </section>
  )
}
