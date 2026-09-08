import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { ErroApi, api, type Bloco } from '../api'
import { Icone } from '../ui/icones'

const PAPEL: Record<string, string> = {
  diretor: 'Diretor', rt: 'RT', gerente: 'Gerente',
  conferente: 'Conferente', comprador: 'Comprador', auditoria: 'Auditoria',
}

/**
 * Compartilhar pelo SISTEMA, não por link.
 *
 * Ganhos sobre um link solto: auditoria de quem compartilhou o quê, revogação,
 * e nenhum segredo em trânsito — link é encaminhado, colado em grupo, fica em
 * histórico.
 *
 * E a regra que não pode quebrar: **compartilhar aponta para uma view, não
 * concede acesso.** Quem abre carrega sob a própria permissão.
 */
export function Compartilhar({
  atorId, titulo, blocos, schema, aoFechar,
}: { atorId: string; titulo: string; blocos: Bloco[]; schema: unknown; aoFechar: () => void }) {
  const [escolhido, setEscolhido] = useState('')
  const [mensagem, setMensagem] = useState('')
  const [estado, setEstado] = useState<'edicao' | 'enviando' | 'enviado'>('edicao')
  const [erro, setErro] = useState('')
  const esquema = schema ?? { versao: 1, blocos: blocos.map((b) => ({ tipo: b.tipo, params: b.params })) }
  // A chave carrega o ator E o schema: a lista depende dos dois. Sem o ator,
  // o cache serve a lista de quem estava logado antes (ADR-0008).
  const pessoas = useQuery({
    queryKey: [atorId, 'destinatarios', esquema],
    queryFn: () => api.destinatarios(esquema),
  })

  async function enviar() {
    if (!escolhido) return
    setEstado('enviando'); setErro('')
    try {
      const v = await api.criarView(titulo, esquema)
      await api.compartilhar(v.view_id, escolhido, mensagem || undefined)
      setEstado('enviado')
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : 'Não foi possível compartilhar.')
      setEstado('edicao')
    }
  }

  return (
    <>
      <button className="veu" onClick={aoFechar} aria-label="Fechar" />
      <div role="dialog" aria-modal="true" aria-label="Compartilhar view" className="dialogo">
        <div className="dialogo-cabeca">
          <span className="titulo-painel">Compartilhar</span>
          <button className="btn btn-icone" onClick={aoFechar} aria-label="Fechar"><Icone.Fechar tamanho={16} /></button>
        </div>

        {estado === 'enviado' ? (
          <div className="dialogo-corpo">
            <p style={{ margin: 0 }}>Entregue na caixa de quem você escolheu.</p>
            <p className="vazio" style={{ marginTop: 10 }}>
              A pessoa abre sob a permissão dela. Se não puder ver algum lote,
              vê “sem acesso” — nunca os seus dados.
            </p>
            <button className="btn btn-primario" style={{ marginTop: 14 }} onClick={aoFechar}>Fechar</button>
          </div>
        ) : (
          <div className="dialogo-corpo">
            <p className="vazio" style={{ marginTop: 0 }}>
              Compartilha-se <strong>o schema</strong>, não os dados — assim o item
              continua correto meses depois. A lista abaixo tem só quem consegue
              abrir <em>esta</em> composição sob a permissão dele.
            </p>

            <fieldset className="lista-destinatarios">
              <legend className="rotulo">Para</legend>
              {pessoas.isPending && <p className="vazio">carregando…</p>}
              {pessoas.data?.map((p) => (
                <label key={p.id} className={`destinatario ${escolhido === p.id ? 'is-escolhido' : ''}`}>
                  <input
                    type="radio" name="destinatario" value={p.id}
                    checked={escolhido === p.id}
                    onChange={() => setEscolhido(p.id)}
                  />
                  <span>
                    <span style={{ fontWeight: 500 }}>{p.nome}</span>
                    <span className="fraco"> · {PAPEL[p.papel] ?? p.papel}</span>
                  </span>
                </label>
              ))}
              {pessoas.data?.length === 0 && (
                <p className="vazio">
                  Ninguém pode abrir esta composição. Mandar assim entregaria
                  uma tela vazia.
                </p>
              )}
            </fieldset>

            <label className="rotulo" htmlFor="msg" style={{ display: 'block', marginTop: 14 }}>
              Mensagem (opcional)
            </label>
            <input
              id="msg" className="compositor-campo" style={{ marginTop: 6, width: '100%' }}
              value={mensagem} onChange={(e) => setMensagem(e.target.value)}
              placeholder="olha o lote da amoxicilina"
            />

            {erro && <p className="msg-erro" style={{ marginTop: 12 }}>{erro}</p>}

            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <button className="btn btn-primario" disabled={!escolhido || estado === 'enviando'} onClick={() => void enviar()}>
                {estado === 'enviando' ? 'enviando…' : 'Enviar'}
              </button>
              <button className="btn" onClick={aoFechar}>Cancelar</button>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
