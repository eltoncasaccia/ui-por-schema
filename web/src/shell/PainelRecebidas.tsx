import { useQuery } from '@tanstack/react-query'
import { api, type Eu } from '../api'

/**
 * Caixa de recebidas — o que outras pessoas mandaram para você.
 *
 * A chave carrega o id do ator, obrigatoriamente. Sem isso o cache serve a
 * caixa de quem estava logado antes: foi o bug de compartilhamento, e é
 * exatamente o que o ADR-0008 manda evitar.
 */
export function PainelRecebidas({
  eu, aoAbrir,
}: { eu: Eu; aoAbrir: (viewId: string, de: string) => void }) {
  const caixa = useQuery({
    queryKey: [eu.id, 'recebidas'],
    queryFn: api.recebidas,
    refetchInterval: 30_000,
  })

  return (
    <div className="painel">
      <div className="painel-cabeca">
        <span className="titulo-painel">
          Recebidas{caixa.data?.length ? ` · ${caixa.data.length}` : ''}
        </span>
      </div>
      <div className="painel-corpo">
        {caixa.isPending && <p className="vazio" style={{ padding: 4 }}>carregando…</p>}
        {caixa.data?.length === 0 && (
          <p className="vazio" style={{ padding: '4px 4px 8px' }}>
            Nada recebido. Quando alguém compartilhar uma tela com você, ela
            aparece aqui — e abre sob a <em>sua</em> permissão.
          </p>
        )}
        {caixa.data?.map((r) => (
          <button key={r.id} className="caixa-item" onClick={() => aoAbrir(r.view_id, r.de)}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>{r.de}</div>
            {r.mensagem && (
              <div className="fraco" style={{ fontSize: 12, overflowWrap: 'anywhere' }}>{r.mensagem}</div>
            )}
            <div className="fraco mono" style={{ fontSize: 11, marginTop: 3 }}>
              {new Date(r.criado_em).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
