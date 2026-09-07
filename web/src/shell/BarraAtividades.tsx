export type PainelId = 'navegacao' | 'fixadas'

interface Props {
  painel: PainelId
  lateralAberta: boolean
  assistenteAberto: boolean
  debugAberto: boolean
  aoPainel: (p: PainelId) => void
  aoAssistente: () => void
  aoDebug: () => void
}

const ITENS: { id: PainelId; glifo: string; rotulo: string }[] = [
  { id: 'navegacao', glifo: '☰', rotulo: 'Catálogo' },
  { id: 'fixadas', glifo: '★', rotulo: 'Views fixadas' },
]

export function BarraAtividades(p: Props) {
  return (
    <nav className="activity-bar" aria-label="Barra de atividades">
      {ITENS.map((it) => (
        <button
          key={it.id}
          className={`activity-item ${p.painel === it.id && p.lateralAberta ? 'is-active' : ''}`}
          onClick={() => p.aoPainel(it.id)}
          title={it.rotulo}
          aria-label={it.rotulo}
          aria-pressed={p.painel === it.id && p.lateralAberta}
        >
          <span aria-hidden="true">{it.glifo}</span>
        </button>
      ))}
      <button
        className={`activity-item ${p.assistenteAberto ? 'is-active' : ''}`}
        onClick={p.aoAssistente}
        title="Assistente"
        aria-label="Assistente"
        aria-pressed={p.assistenteAberto}
      >
        <span aria-hidden="true">✦</span>
      </button>
      <button
        className={`activity-item activity-bottom ${p.debugAberto ? 'is-active' : ''}`}
        onClick={p.aoDebug}
        title="Arquitetura / Execution Trace"
        aria-label="Arquitetura"
        aria-pressed={p.debugAberto}
      >
        <span aria-hidden="true">⌥</span>
      </button>
    </nav>
  )
}
