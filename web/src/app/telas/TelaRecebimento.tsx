import { useQuery } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { api, type Bloco, type Eu } from '../../api'
import { composicaoDaTela } from '../../estado/sessao'
import { Composicao } from '../../render/motor'
import { EVENTO_REPEDIR, type DetalheRepedir } from '../../render/repedir'
import { CabecalhoTela } from '../../shell/CabecalhoTela'
import type { RotaOperacao } from '../layout/rotasOperacao'

/**
 * `/recebimento/novo` — igual à `TelaOperacao`, com uma diferença: o param
 * `ean` nasce DENTRO da view, no leitor de código de barras, e muda a cada
 * caixa lida.
 *
 * Esta tela existe porque alguém precisa ser dono desse param. A view não pode
 * buscar dado (`web/CLAUDE.md`, verificado por `arch-check.ts`) e a rota manda
 * `params: () => ({})` — sem este intermediário o EAN lido morria no
 * componente, que era o achado [A-53](../../../../docs/tasks/ACHADOS.md).
 *
 * O padrão da `TelaSaida.tsx` não servia aqui: lá o `produto_id` é pedido uma
 * vez, num portão **antes** de a tela existir. Aqui são dez leituras no meio do
 * preenchimento, e um portão faria o conferente recomeçar a cada caixa.
 */
export function TelaRecebimento({ rota, eu }: { rota: RotaOperacao; eu: Eu }) {
  const [params, setParams] = useState<Record<string, unknown>>({})
  const catalogo = useQuery({ queryKey: [eu.id, 'catalogo'], queryFn: api.catalogo })
  const comandos = catalogo.data?.find((e) => e.id === rota.componente)?.comandos

  // O evento sobe da view pela árvore do DOM — o mesmo caminho que o de
  // comando já usa (`render/comando.ts`). A tela não conhece a view, só o
  // formato do pedido.
  const aoRepedir = useCallback((e: Event) => {
    const { params: novos } = (e as CustomEvent<DetalheRepedir>).detail
    // Mescla, nunca substitui: a view conhece o que ela mudou, e não o que a
    // rota pôs aqui antes dela existir.
    setParams((atuais) => ({ ...atuais, ...novos }))
  }, [])

  const bloco: Bloco = {
    tipo: rota.componente,
    params,
    tamanho: 'inteira',
    ...(comandos ? { comandos } : {}),
  }

  return (
    <main className="workspace">
      <CabecalhoTela titulo={rota.rotulo} composicao={composicaoDaTela(rota.rotulo, [bloco])} />
      {/* O listener fica no contêiner que ENVOLVE a composição: o nó da view é
          recriado a cada leitura, e um listener preso a ele se perderia
          exatamente na troca que ele existe para observar. */}
      <div
        className="workspace-corpo"
        ref={(n) => {
          n?.addEventListener(EVENTO_REPEDIR, aoRepedir)
        }}
      >
        <Composicao blocos={[bloco]} atorId={eu.id} />
      </div>
    </main>
  )
}
