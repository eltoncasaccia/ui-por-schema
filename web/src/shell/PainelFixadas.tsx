import { sessao, useSessao } from '../estado/sessao'
import type { Bloco } from '../api'

/**
 * Views fixadas. Chaveadas pela viewKey, nunca pelo id da composição.
 *
 * Na v1 o favorito duplicava e a estrela voltava apagada ao reabrir a tela: a
 * chave era o id da composição, criado a cada renderização. Uma view é a mesma
 * view quando o schema é o mesmo (ADR-0021).
 */
export function PainelFixadas({ aoAbrir }: { aoAbrir: (titulo: string, blocos: Bloco[]) => void }) {
  const { fixadas } = useSessao()

  return (
    <div className="panel">
      <h2 className="panel-title">Views fixadas</h2>
      {fixadas.length === 0 ? (
        <p className="muted" style={{ fontSize: 12 }}>
          Nada fixado. Use a estrela no cabeçalho do workspace.
        </p>
      ) : (
        <ul className="nav-list">
          {fixadas.map((f) => (
            <li key={f.viewKey} className="pin-row">
              <button className="nav-item" onClick={() => aoAbrir(f.titulo, f.blocos)}>
                <span className="nav-item-main">{f.titulo}</span>
                <span className="nav-item-sub code">{f.viewKey}</span>
              </button>
              <button
                className="pin-remove"
                title="Desafixar"
                onClick={() => sessao.fixar({ id: '', titulo: f.titulo, origem: 'sistema', blocos: f.blocos, schema: null, viewKey: f.viewKey })}
              >✕</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
