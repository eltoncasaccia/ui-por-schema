import { useEffect, useState } from 'react'
import { api, type Eu, type MudancaUsuario, type UsuarioAdmin } from '../../api'
import { Etiqueta } from '../../ui/Etiqueta'

const PAPEIS = ['diretor', 'rt', 'gerente', 'conferente', 'comprador', 'auditoria']
const UNIDADES: [string, string][] = [
  ['cd-matriz', 'CD Matriz'],
  ['cd-refrigerado', 'CD Refrigerado'],
  ['filial-uberlandia', 'Uberlândia'],
]

function mensagem(e: unknown, padrao: string): string {
  return e instanceof Error ? e.message : padrao
}

/**
 * Gestão de usuários (T-038) — tela com rota, **fora do catálogo** do assistente.
 *
 * Esconder a tela de quem não tem `usuario.gerenciar`, e travar a própria linha,
 * é conforto: quem garante é o servidor, que recusa a requisição direta
 * (ADR-0004). Desativar não exclui ninguém (`RN-A06`).
 */
export function TelaUsuarios({ eu }: { eu: Eu }) {
  const podeGerenciar = eu.permissoes.includes('usuario.gerenciar')
  const [usuarios, setUsuarios] = useState<UsuarioAdmin[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    if (!podeGerenciar) return
    api.usuarios().then(setUsuarios, (e: unknown) => setErro(mensagem(e, 'Falha ao carregar.')))
  }, [podeGerenciar])

  if (!podeGerenciar) {
    return (
      <div className="cartao">
        <div className="cartao-corpo fraco">Seu papel não gerencia usuários.</div>
      </div>
    )
  }

  async function salvar(alvo: UsuarioAdmin, mudanca: MudancaUsuario) {
    setErro(null)
    try {
      const novo = await api.alterarUsuario(alvo.id, mudanca)
      setUsuarios((lista) => lista?.map((u) => (u.id === alvo.id ? { ...u, ...novo } : u)) ?? null)
    } catch (e) {
      setErro(mensagem(e, 'Falha ao salvar.'))
    }
  }

  return (
    <div className="cartao">
      <div className="cartao-cabeca">
        <span className="titulo-painel">Usuários</span>
        <span className="mono fraco" style={{ fontSize: 11 }}>
          papel, unidades e ativação
        </span>
      </div>
      <div className="cartao-corpo">
        {erro && (
          <p style={{ margin: '0 0 12px', fontSize: 13 }}>
            <Etiqueta tom="ruim">{erro}</Etiqueta>
          </p>
        )}
        {usuarios === null ? (
          <p className="fraco" style={{ margin: 0, fontSize: 13 }}>Carregando…</p>
        ) : (
          usuarios.map((u) => {
            const proprio = u.id === eu.id
            return (
              <div key={u.id} style={{ padding: '8px 0', fontSize: 13 }}>
                <div>
                  <strong>{u.nome}</strong> <span className="mono fraco">{u.email}</span>{' '}
                  {!u.ativo && <Etiqueta tom="neutro">desativado</Etiqueta>}
                  {proprio && <span className="fraco"> · você não altera o próprio acesso</span>}
                </div>
                <label>
                  Papel{' '}
                  <select
                    value={u.papel ?? ''}
                    disabled={proprio}
                    onChange={(ev) => void salvar(u, { papel: ev.target.value || null })}
                  >
                    <option value="">sem papel</option>
                    {PAPEIS.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </label>{' '}
                {UNIDADES.map(([id, nome]) => (
                  <label key={id} style={{ marginLeft: 8 }}>
                    <input
                      type="checkbox"
                      checked={u.unidades.includes(id)}
                      disabled={proprio}
                      onChange={() =>
                        void salvar(u, {
                          unidades: u.unidades.includes(id)
                            ? u.unidades.filter((x) => x !== id)
                            : [...u.unidades, id],
                        })
                      }
                    />{' '}
                    {nome}
                  </label>
                ))}{' '}
                <button
                  type="button"
                  disabled={proprio}
                  onClick={() => void salvar(u, { ativo: !u.ativo })}
                >
                  {u.ativo ? 'Desativar' : 'Reativar'}
                </button>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
