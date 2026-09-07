/**
 * Motor de render: schema validado → React.
 *
 * Três regras que este módulo aplica e o modelo não controla:
 *
 * 1. LAYOUT OBEDECE AO COMPONENTE. Cada um declara seu `tamanho` no servidor;
 *    o motor arranja. O schema não tem campo de layout — na v1, deixar o modelo
 *    decidir espremia tabela em tile de 200px.
 * 2. Indicadores adjacentes viram UMA grade — senão cada um vira um cartão
 *    solto e o panorama perde a leitura de conjunto.
 * 3. `sem_acesso` é decisão DAQUI. O modelo nunca soube que existe, e a
 *    mensagem não revela o que seria mostrado (ADR-0014).
 */
import { useQuery } from '@tanstack/react-query'
import { ErroApi, api, type Bloco } from '../api'
import { VIEWS } from '../views/indice'

function Esqueleto() {
  return <div className="indicador tom-neutro" aria-busy="true"><div className="indicador-rotulo">carregando…</div></div>
}

function SemAcesso() {
  return (
    <div className="cartao cartao-corpo">
      <p className="vazio">Sem acesso.</p>
    </div>
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
    return <div className="cartao cartao-corpo"><p className="vazio">Sem view para <code className="mono">{bloco.tipo}</code>.</p></div>
  }
  if (q.isPending) return <Esqueleto />
  if (q.error) {
    const e = q.error
    const negado = e instanceof ErroApi && (e.codigo === 'nao_autorizado' || e.codigo === 'nao_encontrado')
    return negado ? <SemAcesso /> : <div className="cartao cartao-corpo"><p className="vazio">Não foi possível carregar.</p></div>
  }
  return <View vm={q.data} />
}

/** Agrupa indicadores adjacentes numa grade só. */
function agrupar(blocos: Bloco[]): { tipo: 'grade' | 'solo'; itens: Bloco[] }[] {
  const grupos: { tipo: 'grade' | 'solo'; itens: Bloco[] }[] = []
  for (const b of blocos) {
    const ehLinha = b.tamanho === 'linha'
    const ultimo = grupos.at(-1)
    if (ehLinha && ultimo?.tipo === 'grade') ultimo.itens.push(b)
    else grupos.push({ tipo: ehLinha ? 'grade' : 'solo', itens: [b] })
  }
  return grupos
}

export function Composicao({ blocos, atorId }: { blocos: Bloco[]; atorId: string }) {
  return (
    <>
      {agrupar(blocos).map((g, i) =>
        g.tipo === 'grade' ? (
          <div key={i} className="grade-indicadores">
            {g.itens.map((b, j) => <BlocoRender key={`${b.tipo}-${j}`} bloco={b} atorId={atorId} />)}
          </div>
        ) : (
          <BlocoRender key={i} bloco={g.itens[0]!} atorId={atorId} />
        ),
      )}
    </>
  )
}

export { agrupar }
