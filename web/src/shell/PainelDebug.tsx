/**
 * O painel de instrumentos. É como esta POC é JULGADA, em vez de admirada.
 *
 * Herdado da v1, e o mais importante para quem revisa o projeto: mostra o
 * prompt que o modelo recebeu, o schema que ele devolveu, o que foi ACEITO e o
 * que foi REJEITADO, e com que permissões.
 */
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type Eu } from '../api'
import { useSessao } from '../estado/sessao'

type Aba = 'trace' | 'schema' | 'catalogo' | 'ator'
const ABAS: { id: Aba; rotulo: string }[] = [
  { id: 'trace', rotulo: 'Execution Trace' },
  { id: 'schema', rotulo: 'View Schema' },
  { id: 'catalogo', rotulo: 'Catálogo do modelo' },
  { id: 'ator', rotulo: 'Ator e permissões' },
]

export function PainelDebug({ eu, aoFechar }: { eu: Eu; aoFechar: () => void }) {
  const [aba, setAba] = useState<Aba>('trace')
  return (
    <aside className="debug">
      <div className="debug-tabs">
        {ABAS.map((a) => (
          <button key={a.id} className={`debug-tab ${aba === a.id ? 'is-active' : ''}`}
            onClick={() => setAba(a.id)}>{a.rotulo}</button>
        ))}
        <button className="debug-close" onClick={aoFechar} title="Fechar">✕</button>
      </div>
      <div className="debug-body">
        {aba === 'trace' && <AbaTrace />}
        {aba === 'schema' && <AbaSchema />}
        {aba === 'catalogo' && <AbaCatalogo eu={eu} />}
        {aba === 'ator' && <AbaAtor eu={eu} />}
      </div>
    </aside>
  )
}

function AbaTrace() {
  const { traces } = useSessao()
  if (traces.length === 0)
    return <p className="muted">Nenhuma execução ainda. Pergunte algo ao assistente.</p>

  return (
    <div className="trace-list">
      {traces.map((t, i) => (
        <div key={i} className="trace-run">
          <div className="trace-run-head">
            <span className="trace-input">{t.pergunta}</span>
            <span className="trace-times">
              <span className={`badge ${t.trace.schema_valido ? 'badge-good' : 'badge-bad'}`}>
                {t.trace.schema_valido ? 'schema válido' : 'schema rejeitado'}
              </span>
              <span className="trace-duration">{t.trace.ms_ate_primeiro_token} ms</span>
            </span>
          </div>
          <div className="trace-steps">
            <Passo rotulo="origem" valor={`${t.trace.origem} · ${t.trace.modelo}`} />
            <Passo rotulo="modo" valor={t.trace.modo} />
            <Passo rotulo="tokens de entrada" valor={String(t.trace.tokens_entrada)} />
            <Passo rotulo="aceitos" valor={t.trace.aceitos.join(', ') || '—'} bom={t.trace.aceitos.length > 0} />
            <Passo
              rotulo="rejeitados"
              valor={t.trace.rejeitados.map(([tipo, m]) => `${tipo}: ${m}`).join(' · ') || 'nenhum'}
              ruim={t.trace.rejeitados.length > 0}
            />
            {t.trace.erro && <Passo rotulo="erro" valor={t.trace.erro} ruim />}
          </div>
        </div>
      ))}
      <p className="debug-note">
        Componente não registrado é rejeitado e <strong>aparece aqui</strong>. Um
        filtro que falta apenas alarga a resposta, em silêncio — não há erro para
        observar. Foi o achado mais perigoso da v1.
      </p>
    </div>
  )
}

function Passo({ rotulo, valor, bom, ruim }: { rotulo: string; valor: string; bom?: boolean; ruim?: boolean }) {
  return (
    <div className="trace-step">
      <span className="trace-stage">{rotulo}</span>
      <span className={ruim ? 'cell-bad' : bom ? 'cell-good' : ''}>{valor}</span>
    </div>
  )
}

function AbaSchema() {
  const { composicoes, noWorkspace } = useSessao()
  const c = noWorkspace ? composicoes[noWorkspace] : undefined
  if (!c) return <p className="muted">Nada no workspace.</p>
  return (
    <>
      <p className="debug-note">
        Tudo que o modelo produziu. Não existe campo para markup, estilo, valor
        literal ou expressão — o schema <strong>não tem onde carregar código</strong>.
      </p>
      <pre className="code">{JSON.stringify(c.schema ?? c.blocos, null, 2)}</pre>
    </>
  )
}

function AbaCatalogo({ eu }: { eu: Eu }) {
  const q = useQuery({ queryKey: [eu.id, 'catalogo'], queryFn: api.catalogo })
  return (
    <>
      <p className="debug-note">
        Literalmente o que vai no prompt, para <strong>{eu.nome}</strong>. Gerado no
        servidor e filtrado pelas permissões dele — o modelo não consegue propor o
        que não está aqui.
      </p>
      <pre className="code">{JSON.stringify(q.data ?? [], null, 2)}</pre>
    </>
  )
}

function AbaAtor({ eu }: { eu: Eu }) {
  return (
    <div className="state-grid">
      <div className="state-block">
        <h4 className="panel-heading">Ator</h4>
        <pre className="code">{JSON.stringify({ id: eu.id, nome: eu.nome, papel: eu.papel }, null, 2)}</pre>
      </div>
      <div className="state-block">
        <h4 className="panel-heading">Unidades — RN-A01</h4>
        <pre className="code">{JSON.stringify(eu.unidades, null, 2)}</pre>
      </div>
      <div className="state-block">
        <h4 className="panel-heading">Permissões</h4>
        <pre className="code">{JSON.stringify(eu.permissoes, null, 2)}</pre>
      </div>
    </div>
  )
}
