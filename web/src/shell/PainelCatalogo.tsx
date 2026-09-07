import { useQuery } from '@tanstack/react-query'
import { api, type EntradaCatalogo, type Eu } from '../api'

/**
 * O catálogo DESTE ator — o vocabulário que o modelo recebe quando ele pergunta.
 *
 * Mostrar isto na interface é deliberado: é a demonstração mais direta do
 * ADR-0003. Duas pessoas abrem a mesma tela e veem listas diferentes.
 */
export function PainelCatalogo({ eu, aoAbrir }: { eu: Eu; aoAbrir: (c: EntradaCatalogo) => void }) {
  const q = useQuery({ queryKey: [eu.id, 'catalogo'], queryFn: api.catalogo })

  return (
    <div className="panel">
      <h2 className="panel-title">Catálogo · {eu.papel ?? 'sem papel'}</h2>
      <p className="muted" style={{ fontSize: 12, margin: 0, lineHeight: 1.55 }}>
        O vocabulário que o assistente recebe quando <strong>você</strong> pergunta.
        Outro papel recebe outro conjunto.
      </p>

      <div className="panel-section">
        {q.data?.length === 0 && (
          <p className="muted" style={{ fontSize: 12 }}>
            Catálogo vazio — seu usuário não tem papel atribuído. É o comportamento
            correto: cadastro não concede permissão.
          </p>
        )}
        {q.data?.map((c) => (
          <div key={c.id} className="cat-item">
            <div className="cat-head">
              <code className="code">{c.id}</code>
              <button className="ghost-button" onClick={() => aoAbrir(c)}>abrir</button>
            </div>
            <p className="cat-desc">{c.description}</p>
            {Object.entries(c.params).map(([nome, info]) =>
              info.valores ? (
                <div key={nome} className="cat-enum">
                  <span className="muted" style={{ fontSize: 11 }}>{nome}:</span>
                  {info.valores.map((v) => <span key={v} className="enum-valor">{v}</span>)}
                </div>
              ) : null,
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
