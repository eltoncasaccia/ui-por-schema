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
import { useInfiniteQuery } from '@tanstack/react-query'
import { ErroApi, api, type Bloco } from '../api'
import type { ComponentId } from '../generated/componentes'
import { VIEWS } from '../views/indice'
import { useScrollInfinito } from '../ui/useScrollInfinito'

function Esqueleto() {
  return <div className="indicador tom-neutro" aria-busy="true"><div className="indicador-rotulo">carregando…</div></div>
}

/**
 * Bloco negado por ESCOPO DE REGISTRO não renderiza nada.
 *
 * "Sem acesso" num quadro vazio conta o que a regra manda esconder: que existe
 * algo ali. É o ADR-0014 aplicado à interface — no servidor a resposta já é
 * indistinguível de inexistente; se a tela desenhar uma lacuna rotulada, o
 * cuidado do servidor foi desperdiçado.
 *
 * Negativa de ESCOPO DECLARADO (uma unidade) é outro caso e continua explícita:
 * a unidade existe e a pessoa sabe que existe.
 */
function paginado(d: unknown): d is { linhas: unknown[]; cursor: string | null; tem_mais: boolean } {
  return typeof d === 'object' && d !== null && 'tem_mais' in d && 'linhas' in d
}

function BlocoRender({ bloco, atorId }: { bloco: Bloco; atorId: string }) {
  const q = useInfiniteQuery({
    // A identidade do ator entra na chave, obrigatoriamente: sem isso o cache
    // serviria dado de uma pessoa para outra (ADR-0008).
    queryKey: [atorId, bloco.tipo, bloco.params],
    queryFn: ({ pageParam }) => api.dados<unknown>(bloco.tipo, bloco.params, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (ultima) => (paginado(ultima) && ultima.tem_mais ? ultima.cursor : null),
    retry: false,
  })

  const sentinela = useScrollInfinito(
    () => { if (q.hasNextPage && !q.isFetchingNextPage) void q.fetchNextPage() },
    Boolean(q.hasNextPage),
  )

  // `bloco.tipo` é string na borda; o mapa é indexado por ComponentId.
  // O `in` estreita o tipo e cobre o caso de id que a API tem e o cliente não.
  const View = bloco.tipo in VIEWS ? VIEWS[bloco.tipo as ComponentId] : undefined
  if (!View) {
    // Bijeção quebrada: id registrado na API sem view no cliente. Em CI isso
    // falha o build; em runtime, falha visível — nunca silenciosa.
    return <div className="cartao cartao-corpo"><p className="vazio">Sem view para <code className="mono">{bloco.tipo}</code>.</p></div>
  }
  if (q.isPending) return <Esqueleto />
  if (q.error) {
    const e = q.error
    // Registro fora de escopo: NÃO renderiza nada. Ver a nota acima.
    if (e instanceof ErroApi && e.codigo === 'nao_encontrado') return null
    if (e instanceof ErroApi && e.codigo === 'nao_autorizado') {
      return <div className="cartao cartao-corpo"><p className="vazio">{e.message}</p></div>
    }
    return <div className="cartao cartao-corpo"><p className="vazio">Não foi possível carregar.</p></div>
  }

  // Contrato de paginação: um viewmodel que pagina expõe `linhas`, `cursor` e
  // `tem_mais`. O motor concatena `linhas` e entrega UM viewmodel à view — ela
  // não sabe que houve mais de uma requisição.
  const paginas = q.data.pages
  const primeira = paginas[0]
  const vm = paginado(primeira)
    ? { ...primeira, linhas: paginas.flatMap((p) => (paginado(p) ? p.linhas : [])) }
    : primeira

  return (
    <>
      <View vm={vm} />
      {q.hasNextPage && (
        <div ref={sentinela} className="sentinela" aria-hidden="true">
          {q.isFetchingNextPage ? 'carregando mais…' : ''}
        </div>
      )}
    </>
  )
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
