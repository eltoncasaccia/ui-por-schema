import { useEffect, useState } from 'react'
import { api, ErroApi, type Bloco, type Eu } from './api'
import { Roteador } from './app/layout/Roteador'
import { caminhoDaView, irPara, useRotaView } from './app/rotas'
import { limparAoSair } from './estado/cache'
import { sessao, useSessao, viewKeyLocal } from './estado/sessao'
import { Compartilhar } from './shell/Compartilhar'
import { Login } from './shell/Login'
import { PainelAssistente } from './shell/PainelAssistente'
import { PainelDebug } from './shell/PainelDebug'
import { PainelFixadas } from './shell/PainelFixadas'
import { PainelRecebidas } from './shell/PainelRecebidas'
import { MENU, PainelNavegacao, type ItemNav } from './shell/PainelNavegacao'
import { Workspace } from './shell/Workspace'
import { Icone } from './ui/icones'
import { useDivisor } from './ui/useDivisor'
import { LIMITE_ESTREITO, useLargura } from './ui/useLargura'
import { useTema } from './ui/useTema'

type PainelId = 'navegacao' | 'fixadas' | 'recebidas'

/**
 * O shell — estrutura fixa, conteúdo adaptável.
 *
 * O assistente é UMA superfície, ao lado do workspace — não o app inteiro
 * (§11.2 e §11.5 da arquitetura). Por isso a navegação convencional continua
 * existindo, e por isso uma composição do assistente só entra no workspace
 * quando a pessoa manda.
 */
export function App() {
  const [eu, setEu] = useState<Eu | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [painel, setPainel] = useState<PainelId | null>('navegacao')
  const [assistente, setAssistente] = useState(true)
  const [debug, setDebug] = useState(false)
  const [itemAtual, setItemAtual] = useState<string | null>(null)
  const [erroRota, setErroRota] = useState<string | null>(null)
  const [tema, setTema] = useTema()
  // Vem da sessão, e não de estado local: o botão de compartilhar mora em
  // qualquer tela — rota, workspace ou conversa —, e nenhuma delas é filha daqui.
  const { compartilhando } = useSessao()
  const largura = useLargura()
  const { viewId } = useRotaView()

  const lateral = useDivisor(272, 200, 460, 'esquerda')
  const dock = useDivisor(380, 300, 620, 'direita')

  useEffect(() => {
    api.eu().then(setEu).catch(() => setEu(null)).finally(() => setCarregando(false))
  }, [])

  // Ao estreitar, painel e assistente viram sobreposição. Deixar os dois
  // abertos empilha um sobre o outro e some com o workspace — o que a captura
  // mostrava. Ao estreitar, recolhe; ao alargar, devolve o assistente.
  useEffect(() => {
    if (largura < LIMITE_ESTREITO) { setPainel(null); setAssistente(false) }
    else setAssistente(true)
  }, [largura])

  /**
   * `/v/:viewId` — o endereço é o estado de entrada (T-016 AC-4).
   *
   * Recarregar reproduz a MESMA tela porque o schema vem do servidor pelo id,
   * e não de memória local, que o reload apaga — era o bug do favorito da v1.
   *
   * E o schema é revalidado contra o catálogo de QUEM ABRE, no servidor
   * (`/api/views/{id}`, ADR-0009 e ADR-0021). Um endereço que carregasse com a
   * permissão de quem criou seria escalação de privilégio disfarçada de
   * conveniência — por isso o cliente não decide nada aqui: pede e desenha.
   */
  useEffect(() => {
    if (!eu || !viewId) { setErroRota(null); return }
    let vivo = true
    api.abrirView(viewId)
      .then((v) => {
        if (!vivo) return
        setErroRota(null)
        sessao.compos({
          id: crypto.randomUUID(),
          titulo: 'Tela compartilhada',
          origem: 'sistema',
          blocos: v.blocos,
          schema: v.schema,
          viewKey: viewKeyLocal(v.blocos),
        })
      })
      .catch((e: unknown) => {
        if (!vivo) return
        // Revogado e inexistente respondem igual, de propósito (ADR-0014). A
        // mensagem aqui é a mesma para os dois pelo mesmo motivo.
        setErroRota(
          e instanceof ErroApi && e.codigo === 'nao_encontrado'
            ? 'Este endereço não está mais disponível.'
            : 'Não foi possível abrir este endereço.',
        )
      })
    return () => { vivo = false }
  }, [eu, viewId])

  if (carregando) return <p className="vazio" style={{ padding: 32 }}>carregando…</p>
  if (!eu) return <Login aoEntrar={setEu} />

  const estreito = largura < LIMITE_ESTREITO

  function abrir(titulo: string, blocos: Bloco[], item: string | null = null) {
    setItemAtual(item)
    // O workspace só está na tela em `/`. Sem voltar para lá, o clique no menu a
    // partir de uma rota (`/lotes`) montava a composição fora da vista (A-45), e
    // um F5 numa view compartilhada reabriria a tela errada.
    irPara('/')
    sessao.compos({
      id: crypto.randomUUID(), titulo, origem: 'sistema', blocos,
      schema: { versao: 1, blocos: blocos.map((b) => ({ tipo: b.tipo, params: b.params })) },
      viewKey: viewKeyLocal(blocos),
    })
    if (estreito) setPainel(null)
  }

  function abrirDoMenu(i: ItemNav) {
    abrir(i.rotulo, [{ tipo: i.componente, params: i.params ?? {}, tamanho: i.componente === 'estoque_indicador' ? 'linha' : 'inteira' }], i.id)
  }

  function abrirRecebida(id: string, _de: string) {
    // Passa a ir pelo ENDEREÇO, e não por uma chamada solta: o efeito de
    // `/v/:viewId` já sabe abrir, revalidar e tratar a negativa. Uma recebida
    // aberta assim fica endereçável — dá para recarregar, favoritar no
    // navegador e mandar o link (que continua não concedendo acesso: quem abre
    // carrega sob a própria permissão).
    irPara(caminhoDaView(id))
  }

  function sair() {
    void api.sair()
    sessao.reset()
    // Segunda camada: sem limpar, dado da sessão anterior sobrevive em memória
    // mesmo com a queryKey correta. As duas existem porque o bug aconteceu.
    limparAoSair()
    setEu(null)
  }

  function alternarPainel(p: PainelId) {
    setPainel((atualP) => (atualP === p ? null : p))
  }

  const iniciais = eu.nome.split(' ').map((n) => n[0]).slice(0, 2).join('')

  return (
    <div className="shell">
      <nav className="barra" aria-label="Barra de atividades">
        <button className={`barra-item ${painel === 'navegacao' ? 'is-ativo' : ''}`}
          onClick={() => alternarPainel('navegacao')} aria-label="Navegação" aria-pressed={painel === 'navegacao'}>
          <Icone.Menu />
        </button>
        <button className={`barra-item ${painel === 'fixadas' ? 'is-ativo' : ''}`}
          onClick={() => alternarPainel('fixadas')} aria-label="Fixadas" aria-pressed={painel === 'fixadas'}>
          <Icone.Estrela />
        </button>
        <button className={`barra-item ${painel === 'recebidas' ? 'is-ativo' : ''}`}
          onClick={() => alternarPainel('recebidas')} aria-label="Recebidas" aria-pressed={painel === 'recebidas'}>
          <Icone.Sino />
        </button>
        <button className={`barra-item ${assistente ? 'is-ativo' : ''}`}
          onClick={() => setAssistente((v) => !v)} aria-label="Assistente" aria-pressed={assistente}>
          <Icone.Faisca />
        </button>
        <button className={`barra-item ${debug ? 'is-ativo' : ''}`}
          onClick={() => setDebug((v) => !v)} aria-label="Execution Trace" aria-pressed={debug}>
          <Icone.Trace />
        </button>

        <button className="barra-item barra-fim"
          onClick={() => setTema(tema === 'escuro' ? 'claro' : 'escuro')}
          aria-label={tema === 'escuro' ? 'Usar tema claro' : 'Usar tema escuro'}>
          {tema === 'escuro' ? <Icone.Sol /> : <Icone.Lua />}
        </button>
        {/* sair mora aqui, no fim da coluna de ícones */}
        <button className="barra-item" onClick={sair} aria-label="Sair">
          <Icone.Sair />
        </button>
      </nav>

      <div className="shell-corpo">
        {painel && estreito && <button className="veu" onClick={() => setPainel(null)} aria-label="Fechar painel" />}
        {painel && (
          <aside className="lateral" style={estreito ? undefined : { width: lateral.largura, flex: 'none' }}>
            {painel === 'navegacao' && <PainelNavegacao atual={itemAtual} aoAbrir={abrirDoMenu} atorId={eu.id} />}
            {painel === 'fixadas' && <PainelFixadas aoAbrir={(t, b) => abrir(t, b)} />}
            {painel === 'recebidas' && (
              <PainelRecebidas eu={eu} aoAbrir={abrirRecebida} />
            )}
            {/* usuário logado, fixo no rodapé */}
            <div className="rodape-ator">
              <div className="avatar" aria-hidden="true">{iniciais}</div>
              <div style={{ minWidth: 0 }}>
                <div className="ator-nome">{eu.nome}</div>
                <div className="ator-sub">
                  {eu.papel ?? 'sem papel'} · {eu.unidades.length} unidade{eu.unidades.length === 1 ? '' : 's'}
                </div>
              </div>
            </div>
          </aside>
        )}
        {painel && !estreito && (
          <div className="divisor" role="separator" tabIndex={0} aria-label="Redimensionar navegação"
            aria-orientation="vertical" onPointerDown={lateral.aoDescer} onKeyDown={lateral.aoTeclado} />
        )}

        {erroRota && (
          <div role="status" className="vazio" style={{ padding: 32, flex: 1, minWidth: 0 }}>
            {erroRota}
            <div style={{ marginTop: 12 }}>
              <button type="button" className="btn" onClick={() => irPara('/')}>
                Voltar
              </button>
            </div>
          </div>
        )}
        {!erroRota && <Roteador eu={eu} workspace={<Workspace eu={eu} />} />}

        {assistente && !estreito && (
          <div className="divisor" role="separator" tabIndex={0} aria-label="Redimensionar assistente"
            aria-orientation="vertical" onPointerDown={dock.aoDescer} onKeyDown={dock.aoTeclado} />
        )}
        {assistente && (
          <>
            {estreito && <button className="veu" onClick={() => setAssistente(false)} aria-label="Fechar assistente" />}
            <aside className="assistente-dock" style={estreito ? undefined : { width: dock.largura, flex: 'none' }}>
              <PainelAssistente eu={eu} aoFechar={() => setAssistente(false)} />
            </aside>
          </>
        )}
      </div>

      {debug && <PainelDebug eu={eu} aoFechar={() => setDebug(false)} />}

      {compartilhando && (
        <Compartilhar
          atorId={eu.id} titulo={compartilhando.titulo}
          blocos={compartilhando.blocos} schema={compartilhando.schema}
          aoFechar={() => sessao.compartilhar(null)}
        />
      )}
    </div>
  )
}

export { MENU }
