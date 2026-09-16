import { useParams } from 'react-router-dom'
import type { Bloco, Eu } from '../../api'
import { composicaoDaTela } from '../../estado/sessao'
import { Composicao } from '../../render/motor'
import { CabecalhoTela } from '../../shell/CabecalhoTela'
import type { RotaOperacao } from '../layout/rotasOperacao'

/**
 * A tela genérica de uma rota de operação: monta o MESMO bloco que o
 * assistente montaria para este componente, e entrega ao MESMO motor de
 * render (`Composicao`) — é a prova em código do ADR-0005 (AC-1). Não existe
 * aqui um segundo caminho de busca de dado: quem busca é `Composicao`, pelo
 * `api.dados` de sempre, nunca `api.compor` (AC-2, §11.5).
 */
export function TelaOperacao({ rota, eu }: { rota: RotaOperacao; eu: Eu }) {
  const urlParams = useParams()
  const bloco: Bloco = { tipo: rota.componente, params: rota.params(urlParams), tamanho: 'inteira' }

  return (
    <main className="workspace">
      <CabecalhoTela titulo={rota.rotulo} composicao={composicaoDaTela(rota.rotulo, [bloco])} />
      <div className="workspace-corpo">
        <Composicao blocos={[bloco]} atorId={eu.id} />
      </div>
    </main>
  )
}
