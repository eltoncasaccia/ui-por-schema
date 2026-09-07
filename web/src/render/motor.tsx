/**
 * Motor de render: schema validado → React. ADR-0007, ADR-0015 (layout).
 *
 * Duas regras que este módulo aplica e o modelo não controla:
 *
 * 1. LAYOUT OBEDECE AO COMPONENTE, não ao modelo. Cada componente declara seu
 *    `tamanho` no servidor; o motor arranja. O schema não tem campo de layout —
 *    na v1, deixar o modelo decidir espremia tabela em tile de 200px.
 *
 * 2. `sem_acesso` é decisão DAQUI, não composição. O modelo nunca soube que ele
 *    existe, e a mensagem não revela o que seria mostrado (ADR-0014).
 */
import { useQuery } from '@tanstack/react-query'
import { ErroApi, api, type Bloco } from '../api'
import { VIEWS } from '../views/indice'

const LARGURA: Record<string, string> = {
  linha: 'span 3',
  meia: 'span 6',
  inteira: 'span 12',
  alta: 'span 12',
}

function Moldura({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="cartao" style={{ padding: '1rem 1.1rem' }}>
      <h3 style={{ fontSize: '.9rem', marginBottom: '.6rem', color: 'var(--suave)' }}>{titulo}</h3>
      {children}
    </section>
  )
}

function BlocoRender({ bloco, atorId }: { bloco: Bloco; atorId: string }) {
  const q = useQuery({
    // A identidade do ator entra na chave, obrigatoriamente: sem isso o cache
    // serviria dado de uma pessoa para outra (ADR-0008).
    queryKey: [atorId, bloco.tipo, bloco.params],
    queryFn: () => api.dados<unknown>(bloco.tipo, bloco.params),
    retry: false,
  })

  const View = VIEWS[bloco.tipo]
  if (!View) {
    // Bijeção quebrada: id registrado na API sem view no cliente. Em CI isso
    // falha o build; em runtime, falha visível — nunca silenciosa.
    return <Moldura titulo={bloco.tipo}><p className="suave">Sem view registrada para este componente.</p></Moldura>
  }
  if (q.isPending) return <Moldura titulo={bloco.tipo}><p className="suave">carregando…</p></Moldura>
  if (q.error) {
    const e = q.error
    const negado = e instanceof ErroApi && (e.codigo === 'nao_autorizado' || e.codigo === 'nao_encontrado')
    return (
      <Moldura titulo={bloco.tipo}>
        <p className="suave">{negado ? 'Sem acesso.' : 'Não foi possível carregar.'}</p>
      </Moldura>
    )
  }
  return <Moldura titulo={bloco.tipo}><View vm={q.data} /></Moldura>
}

export function Composicao({ blocos, atorId }: { blocos: Bloco[]; atorId: string }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '1rem' }}>
      {blocos.map((b, i) => (
        <div key={`${b.tipo}-${i}`} style={{ gridColumn: LARGURA[b.tamanho] ?? 'span 12' }}>
          <BlocoRender bloco={b} atorId={atorId} />
        </div>
      ))}
    </div>
  )
}
