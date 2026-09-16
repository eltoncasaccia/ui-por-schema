import type { ReactNode } from 'react'
import { sessao, useSessao, type Composicao } from '../estado/sessao'
import { Icone } from '../ui/icones'

/**
 * O cabeçalho de toda tela que mostra componentes: o título e as duas ações
 * que valem para qualquer uma, fixar e compartilhar.
 *
 * Elas viviam só no workspace — quem abria Lotes pela rota não tinha como
 * guardar nem repassar a tela, e a mesma informação ganhava ações diferentes
 * conforme o caminho por onde se chegou.
 */
export function CabecalhoTela({
  titulo, composicao, children,
}: { titulo: string; composicao?: Composicao; children?: ReactNode }) {
  const { fixadas } = useSessao()
  const fixada = composicao !== undefined && fixadas.some((f) => f.viewKey === composicao.viewKey)

  return (
    <header className="workspace-cabeca">
      <div style={{ minWidth: 0 }}>
        <h1 className="workspace-titulo" style={{ overflowWrap: 'anywhere' }}>{titulo}</h1>
        {children && <div className="workspace-sub">{children}</div>}
      </div>
      {composicao && (
        <div className="workspace-acoes">
          {/* Só a estrela: o rótulo repetia o que o ícone já diz, e o estado
              (fixada ou não) fica no preenchimento, não num texto. */}
          <button className={`estrela ${fixada ? 'is-fixada' : ''}`} onClick={() => sessao.fixar(composicao)}
            aria-pressed={fixada} aria-label={fixada ? 'Desafixar view' : 'Fixar view'}
            title={fixada ? 'Desafixar' : 'Fixar'}>
            <Icone.Estrela tamanho={16} preenchida={fixada} />
          </button>
          <button className="btn" onClick={() => sessao.compartilhar(composicao)} aria-label="Compartilhar view">
            <Icone.Compartilhar tamanho={15} /> <span className="so-largo">Compartilhar</span>
          </button>
        </div>
      )}
    </header>
  )
}
