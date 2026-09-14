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
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useRef, useState } from 'react'
import { ErroApi, api, type Bloco } from '../api'
import type { ComponentId } from '../generated/componentes'
import { EVENTO_COMANDO, chaveIdempotencia, type DetalheComando } from './comando'
import { classeTexto } from '../ui/estados'
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

/** Uma tentativa de comando em curso — armada, em voo, ou com erro. */
interface Tentativa {
  acao: string
  endpoint: string
  corpo: Record<string, unknown>
  // Uma por INVOCAÇÃO (T-049 AC-3), reaproveitada por qualquer retentativa
  // desta MESMA tentativa (AC-8) — nunca regenerada aqui.
  chave: string
  // Lido no instante em que a tentativa é armada (T-050) — o mesmo valor
  // segue em qualquer retentativa desta tentativa; mudar de etag no meio é
  // outra tentativa, com outra chave.
  etag: string | undefined
  enviando: boolean
  erro: string | null
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

  // O canal de escrita (T-049). A view despacha `comando`; este contêiner é
  // quem escuta, quem chama a rede e quem decide se um segundo clique é
  // exigido primeiro — a view nunca soube que rede existe.
  const [tentativa, setTentativa] = useState<Tentativa | null>(null)
  const qc = useQueryClient()

  const enviar = useCallback(
    (t: Tentativa) => {
      setTentativa({ ...t, enviando: true, erro: null })
      api.comando(t.endpoint, t.corpo, t.chave, t.etag)
        .then(() => {
          setTentativa(null)
          // O que a tela mostra (saldo, status) mudou — a MESMA leitura que a
          // rota tradicional e o assistente usam precisa refletir isso.
          void qc.invalidateQueries({ queryKey: [atorId, bloco.tipo, bloco.params] })
        })
        .catch((e: unknown) => {
          const msg = e instanceof ErroApi ? e.message : 'Não foi possível concluir.'
          // Nada de estado otimista: o `vm` da leitura não é tocado, então a
          // tela continua mostrando o que mostrava antes do clique (AC-4).
          setTentativa((cur) => (cur && cur.chave === t.chave ? { ...cur, enviando: false, erro: msg } : cur))
        })
    },
    [qc, atorId, bloco.tipo, bloco.params],
  )

  // `enviar` e `bloco.comandos` mudam de identidade a cada render; o listener
  // não pode. Um ref por trás resolve sem reataching a cada render — e sem
  // depender de `useEffect`, que só reage a MUDANÇA de dependência, não ao
  // contêiner aparecer pela primeira vez depois do `Esqueleto` (o bug que a
  // primeira versão desta tarefa tinha: o nó só existe depois do carregamento
  // inicial, e as dependências do efeito não mudam nesse instante).
  const enviarAtual = useRef(enviar)
  enviarAtual.current = enviar
  const comandosAtual = useRef(bloco.comandos)
  comandosAtual.current = bloco.comandos
  const blocoAtual = useRef(bloco)
  blocoAtual.current = bloco
  const ligado = useRef<{ el: Element; fn: (ev: Event) => void } | null>(null)

  const contRef = useCallback((el: HTMLDivElement | null) => {
    if (ligado.current) {
      ligado.current.el.removeEventListener(EVENTO_COMANDO, ligado.current.fn)
      ligado.current = null
    }
    if (!el) return
    function aoComando(ev: Event): void {
      const { acao, corpo } = (ev as CustomEvent<DetalheComando>).detail
      const cmd = comandosAtual.current?.[acao]
      if (!cmd) return
      // T-050: o etag lido na ÚLTIMA leitura deste bloco — `undefined` para
      // os comandos que ainda não têm etag na leitura (achado A-41, o resto
      // fica para T-051). O servidor recusa com "If-Match obrigatorio" nesse
      // caso, exatamente como fazia antes desta tarefa.
      const etag = api.etagAtual(blocoAtual.current.tipo, blocoAtual.current.params)
      const t: Tentativa = {
        acao,
        endpoint: cmd.endpoint,
        corpo,
        chave: chaveIdempotencia(),
        etag,
        enviando: false,
        erro: null,
      }
      // `confirm: true` arma e espera o segundo clique (AC-2) — um só nunca
      // escreve. `confirm: false` segue direto.
      if (cmd.confirm) setTentativa(t)
      else enviarAtual.current(t)
    }
    el.addEventListener(EVENTO_COMANDO, aoComando)
    ligado.current = { el, fn: aoComando }
  }, [])

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
    <div ref={contRef}>
      <View vm={vm} />
      {tentativa && (
        <div className="cartao cartao-corpo" role="status" style={{ marginTop: 8 }}>
          {tentativa.erro ? (
            <>
              <p className={classeTexto('ruim')}>{tentativa.erro}</p>
              <div style={{ display: 'flex', gap: 8 }}>
                <button type="button" className="btn" onClick={() => setTentativa(null)}>Cancelar</button>
                <button type="button" className="btn btn-primario" onClick={() => enviar(tentativa)}>Tentar novamente</button>
              </div>
            </>
          ) : tentativa.enviando ? (
            <p className="vazio">Enviando…</p>
          ) : (
            <>
              <p>Confirmar esta ação?</p>
              <div style={{ display: 'flex', gap: 8 }}>
                <button type="button" className="btn" onClick={() => setTentativa(null)}>Cancelar</button>
                <button type="button" className="btn btn-primario" onClick={() => enviar(tentativa)}>Confirmar</button>
              </div>
            </>
          )}
        </div>
      )}
      {q.hasNextPage && (
        <div ref={sentinela} className="sentinela" aria-hidden="true">
          {q.isFetchingNextPage ? 'carregando mais…' : ''}
        </div>
      )}
    </div>
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
