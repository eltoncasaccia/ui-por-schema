import { useQuery } from '@tanstack/react-query'
import { api, type Bloco } from '../api'
import { sessao, useSessao } from '../estado/sessao'
import { Icone } from '../ui/icones'

/**
 * Views fixadas + caixa de recebidas.
 *
 * Fixadas são chaveadas pela viewKey, nunca pelo id da composição: na v1 o
 * favorito duplicava e a estrela voltava apagada ao reabrir, porque a chave era
 * criada a cada renderização (ADR-0021).
 */
export function PainelFixadas({
  aoAbrir, aoAbrirRecebida,
}: { aoAbrir: (titulo: string, blocos: Bloco[]) => void; aoAbrirRecebida: (viewId: string, de: string) => void }) {
  const { fixadas } = useSessao()
  const caixa = useQuery({ queryKey: ['recebidas'], queryFn: api.recebidas, refetchInterval: 30_000 })

  return (
    <div className="painel">
      <div className="painel-cabeca"><span className="titulo-painel">Fixadas e recebidas</span></div>
      <div className="painel-corpo">
        <div className="rotulo" style={{ padding: '8px 4px 6px' }}>Fixadas</div>
        {fixadas.length === 0 ? (
          <p className="vazio" style={{ padding: '0 4px 8px' }}>Use a estrela no cabeçalho.</p>
        ) : (
          fixadas.map((f) => (
            <div key={f.viewKey} style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <button className="nav-item" style={{ flex: 1, minWidth: 0 }} onClick={() => aoAbrir(f.titulo, f.blocos)}>
                <span className="nav-icone"><Icone.Estrela tamanho={16} /></span>
                <span className="nav-titulo" style={{ overflowWrap: 'anywhere' }}>{f.titulo}</span>
                <span className="nav-sub mono">{f.viewKey}</span>
              </button>
              <button
                className="btn btn-icone" aria-label={`Desafixar ${f.titulo}`}
                onClick={() => sessao.fixar({ id: '', titulo: f.titulo, origem: 'sistema', blocos: f.blocos, schema: null, viewKey: f.viewKey })}
              ><Icone.Fechar tamanho={14} /></button>
            </div>
          ))
        )}

        <div className="rotulo" style={{ padding: '16px 4px 6px' }}>
          Recebidas{caixa.data?.length ? ` (${caixa.data.length})` : ''}
        </div>
        {caixa.data?.length === 0 && <p className="vazio" style={{ padding: '0 4px' }}>Nada recebido.</p>}
        {caixa.data?.map((r) => (
          <button key={r.id} className="caixa-item" onClick={() => aoAbrirRecebida(r.view_id, r.de)}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>{r.de}</div>
            {r.mensagem && <div className="fraco" style={{ fontSize: 12, overflowWrap: 'anywhere' }}>{r.mensagem}</div>}
            <div className="fraco mono" style={{ fontSize: 11, marginTop: 2 }}>
              {new Date(r.criado_em).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
