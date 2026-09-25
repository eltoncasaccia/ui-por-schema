import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { api, type Bloco, type Eu } from '../../api'
import { composicaoDaTela } from '../../estado/sessao'
import { Composicao } from '../../render/motor'
import { CabecalhoTela } from '../../shell/CabecalhoTela'

/**
 * `/saida` é a exceção da tabela: `movimento_saida.Params.produto_id` é
 * obrigatório, e não há como tirá-lo da URL sem um `:id` — que o corte da
 * tarefa não previu, e não há componente de BUSCA de produto no catálogo do
 * ciclo 1 (nenhum recorte é texto livre; toda busca teria de ser um `load`
 * novo, fora do escopo desta tarefa).
 *
 * A saída: o mesmo padrão que `lote_detalhe` e `quarentena_liberar` já usam —
 * identificador digitado ou colado, não buscado — mais um `?produto_id=` na
 * URL para quem chega de um link. Depois de resolvido, é a MESMA
 * `Composicao` com o MESMO `movimento_saida` das outras rotas (AC-1).
 *
 * `comandos` vem do `/api/catalogo` (achado da T-057) — ver o comentário
 * equivalente em `TelaOperacao.tsx`. Sem isto, "Registrar saída" nunca chega
 * ao servidor.
 */
export function TelaSaida({ eu }: { eu: Eu }) {
  const catalogo = useQuery({ queryKey: [eu.id, 'catalogo'], queryFn: api.catalogo })
  const comandos = catalogo.data?.find((e) => e.id === 'movimento_saida')?.comandos
  const [buscaParams] = useSearchParams()
  const daUrl = buscaParams.get('produto_id') ?? ''
  const [produtoId, setProdutoId] = useState(daUrl)
  const [confirmado, setConfirmado] = useState(daUrl !== '')

  if (!confirmado) {
    return (
      <main className="workspace">
        {/* Sem produto ainda não há tela para fixar nem compartilhar. */}
        <CabecalhoTela titulo="Saída" />
        <div className="workspace-corpo">
          <div className="cartao cartao-corpo">
            <p className="vazio">Informe o id do produto para começar a separação.</p>
            <form
              style={{ display: 'flex', gap: 8, marginTop: 8 }}
              onSubmit={(e) => {
                e.preventDefault()
                if (produtoId.trim()) setConfirmado(true)
              }}
            >
              <input
                className="campo"
                value={produtoId}
                onChange={(e) => setProdutoId(e.target.value)}
                placeholder="id do produto"
                aria-label="Id do produto"
              />
              <button type="submit" className="btn btn-primario">Continuar</button>
            </form>
          </div>
        </div>
      </main>
    )
  }

  const bloco: Bloco = {
    tipo: 'movimento_saida',
    params: { produto_id: produtoId },
    tamanho: 'inteira',
    ...(comandos ? { comandos } : {}),
  }
  return (
    <main className="workspace">
      <CabecalhoTela titulo="Saída" composicao={composicaoDaTela('Saída', [bloco])} />
      <div className="workspace-corpo">
        <Composicao blocos={[bloco]} atorId={eu.id} />
      </div>
    </main>
  )
}
