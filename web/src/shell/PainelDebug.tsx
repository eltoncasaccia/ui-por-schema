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
      <div className="debug-abas">
        {ABAS.map((a) => (
          <button key={a.id} className={`debug-aba ${aba === a.id ? 'is-ativa' : ''}`}
            onClick={() => setAba(a.id)}>{a.rotulo}</button>
        ))}
        <button className="btn btn-icone" style={{ marginLeft: 'auto' }} onClick={aoFechar} title="Fechar">✕</button>
      </div>
      <div className="debug-corpo">
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
    return <p className="vazio">Nenhuma execução ainda. Pergunte algo ao assistente.</p>

  return (
    <div className="">
      {traces.map((t, i) => (
        <div key={i} className="trace-item">
          <div className="trace-cabeca">
            <span className="trace-pergunta">{t.pergunta}</span>
            <span style={{ display: 'flex', gap: 10, alignItems: 'center', flex: 'none' }}>
              <span className={`etiqueta ${t.trace.schema_valido ? 'etiqueta-bom' : 'etiqueta-ruim'}`}>
                {t.trace.schema_valido ? 'schema válido' : 'schema rejeitado'}
              </span>
              <span className="mono fraco" style={{ fontSize: 11 }}>{t.trace.ms_ate_primeiro_token} ms</span>
            </span>
          </div>
          <div className="trace-passos">
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
      <p className="debug-nota">
        Componente não registrado é rejeitado e <strong>aparece aqui</strong>. Um
        filtro que falta apenas alarga a resposta, em silêncio — não há erro para
        observar. Foi o achado mais perigoso da v1.
      </p>
    </div>
  )
}

function Passo({ rotulo, valor, bom, ruim }: { rotulo: string; valor: string; bom?: boolean; ruim?: boolean }) {
  return (
    <>
      <span>{rotulo}</span>
      <span className={ruim ? 'texto-ruim' : bom ? 'texto-bom' : ''}>{valor}</span>
    </>
  )
}

function AbaSchema() {
  const { composicoes, noWorkspace } = useSessao()
  const c = noWorkspace ? composicoes[noWorkspace] : undefined
  if (!c) return <p className="vazio">Nada no workspace.</p>
  return (
    <>
      <p className="debug-nota">
        Tudo que o modelo produziu. Não existe campo para markup, estilo, valor
        literal ou expressão — o schema <strong>não tem onde carregar código</strong>.
      </p>
      <pre className="codigo">{JSON.stringify(c.schema ?? c.blocos, null, 2)}</pre>
    </>
  )
}

function AbaCatalogo({ eu }: { eu: Eu }) {
  const q = useQuery({ queryKey: [eu.id, 'catalogo'], queryFn: api.catalogo })
  return (
    <>
      <p className="debug-nota">
        Literalmente o que vai no prompt, para <strong>{eu.nome}</strong>. Gerado no
        servidor e filtrado pelas permissões dele — o modelo não consegue propor o
        que não está aqui.
      </p>
      <pre className="codigo">{JSON.stringify(q.data ?? [], null, 2)}</pre>
    </>
  )
}

function AbaAtor({ eu }: { eu: Eu }) {
  return (
    <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}>
      <div >
        <h4 className="rotulo">Ator</h4>
        <pre className="codigo">{JSON.stringify({ id: eu.id, nome: eu.nome, papel: eu.papel }, null, 2)}</pre>
      </div>
      <div >
        <h4 className="rotulo">Unidades — RN-A01</h4>
        <pre className="codigo">{JSON.stringify(eu.unidades, null, 2)}</pre>
      </div>
      <div >
        <h4 className="rotulo">Permissões</h4>
        <pre className="codigo">{JSON.stringify(eu.permissoes, null, 2)}</pre>
      </div>
    </div>
  )
}
