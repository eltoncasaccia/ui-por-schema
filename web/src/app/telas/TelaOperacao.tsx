import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { api, type Bloco, type Eu } from '../../api'
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
 *
 * `comandos` vem do `/api/catalogo` (achado da T-057), pela MESMA `queryKey`
 * que `PainelNavegacao` já usa — o cache do menu serve esta tela de graça na
 * maioria das vezes. Sem isto, o botão de escrita de um componente aberto por
 * rota fica morto: o clique dispara o evento, mas `BlocoRender` descarta por
 * `bloco.comandos` estar ausente, porque esta tela nunca passou pelas duas
 * rotas que normalmente anexam isto (`/api/assistente/compor`,
 * `/api/views/{id}` — CONTRATOS §6/§8).
 */
export function TelaOperacao({ rota, eu }: { rota: RotaOperacao; eu: Eu }) {
  const urlParams = useParams()
  const catalogo = useQuery({ queryKey: [eu.id, 'catalogo'], queryFn: api.catalogo })
  const comandos = catalogo.data?.find((e) => e.id === rota.componente)?.comandos
  const bloco: Bloco = {
    tipo: rota.componente,
    params: rota.params(urlParams),
    tamanho: 'inteira',
    ...(comandos ? { comandos } : {}),
  }

  return (
    <main className="workspace">
      <CabecalhoTela titulo={rota.rotulo} composicao={composicaoDaTela(rota.rotulo, [bloco])} />
      <div className="workspace-corpo">
        <Composicao blocos={[bloco]} atorId={eu.id} />
      </div>
    </main>
  )
}
