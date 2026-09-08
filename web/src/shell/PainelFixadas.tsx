import type { Bloco } from '../api'
import { sessao, useSessao } from '../estado/sessao'
import { Icone } from '../ui/icones'

/**
 * Só as views fixadas.
 *
 * Recebidas saíram daqui: guardar o que EU marquei junto com o que ALGUÉM me
 * mandou mistura duas coisas com donos, tempos e ações diferentes. Uma é
 * biblioteca, a outra é caixa de entrada.
 *
 * Chaveadas pela viewKey, nunca pelo id da composição: na v1 o favorito
 * duplicava e a estrela voltava apagada ao reabrir (ADR-0021).
 */
export function PainelFixadas({ aoAbrir }: { aoAbrir: (titulo: string, blocos: Bloco[]) => void }) {
  const { fixadas } = useSessao()

  return (
    <div className="painel">
      <div className="painel-cabeca"><span className="titulo-painel">Fixadas</span></div>
      <div className="painel-corpo">
        {fixadas.length === 0 ? (
          <p className="vazio" style={{ padding: '4px 4px 8px' }}>
            Nada fixado. Use a estrela no cabeçalho de uma tela.
          </p>
        ) : (
          fixadas.map((f) => (
            <div key={f.viewKey} className="fixada-linha">
              <button className="nav-item" onClick={() => aoAbrir(f.titulo, f.blocos)}>
                <span className="nav-icone" />
                <span className="nav-titulo" style={{ overflowWrap: 'anywhere' }}>{f.titulo}</span>
                <span className="nav-sub mono">{f.viewKey}</span>
              </button>
              {/* A própria estrela desafixa — um "x" ao lado seria um segundo
                  controle para a mesma ação. */}
              <button
                className="estrela is-fixada fixada-estrela"
                aria-label={`Desafixar ${f.titulo}`} title="Desafixar"
                onClick={() => sessao.fixar({ id: '', titulo: f.titulo, origem: 'sistema', blocos: f.blocos, schema: null, viewKey: f.viewKey })}
              ><Icone.Estrela tamanho={16} preenchida /></button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
