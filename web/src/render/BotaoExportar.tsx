import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { ErroApi, api, type FormatoExportacao } from '../api'
import { classeTexto } from '../ui/estados'

const FORMATOS: readonly { formato: FormatoExportacao; rotulo: string }[] = [
  { formato: 'csv', rotulo: 'CSV' },
  { formato: 'xlsx', rotulo: 'Planilha (.xlsx)' },
  { formato: 'pdf', rotulo: 'PDF' },
]

function baixar(arquivo: Blob, nome: string): void {
  const url = URL.createObjectURL(arquivo)
  const a = document.createElement('a')
  a.href = url
  a.download = nome
  a.click()
  URL.revokeObjectURL(url)
}

/**
 * Exportar um bloco (T-054). O arquivo é gerado no servidor a partir dos
 * mesmos params da tela, com a permissão de quem clica. Aqui não se monta
 * dado nenhum: o que a tela já tem não é reaproveitado, para o arquivo nunca
 * depender do que o navegador guardou.
 *
 * Aparece só para o que o catálogo DESTE ator marca como exportável. O
 * catálogo já está em cache (o assistente o lê), então isso não custa uma
 * requisição por bloco.
 */
export function BotaoExportar({
  tipo, params, atorId,
}: { tipo: string; params: Record<string, unknown>; atorId: string }) {
  // Mesma chave do painel do assistente: um cache só. O wrapper lê `api.catalogo`
  // na hora da busca, e não na montagem.
  const cat = useQuery({ queryKey: [atorId, 'catalogo'], queryFn: () => api.catalogo() })
  const [aberto, setAberto] = useState(false)
  const [gerando, setGerando] = useState<FormatoExportacao | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const raiz = useRef<HTMLDivElement>(null)

  // Menu aberto fecha com Esc ou clique fora, como qualquer menu do sistema.
  useEffect(() => {
    if (!aberto) return
    const fora = (e: MouseEvent) => {
      if (!raiz.current?.contains(e.target as Node)) setAberto(false)
    }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setAberto(false) }
    document.addEventListener('mousedown', fora)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', fora)
      document.removeEventListener('keydown', esc)
    }
  }, [aberto])

  if (!cat.data?.some((c) => c.id === tipo && c.exportavel)) return null

  async function exportar(formato: FormatoExportacao) {
    setAberto(false)
    setErro(null)
    setGerando(formato)
    try {
      const { arquivo, nome } = await api.exportar(tipo, params, formato)
      baixar(arquivo, nome)
    } catch (e) {
      // A mensagem do servidor é pública por construção (ADR-0014), e a do
      // teto diz o que fazer: estreitar o filtro.
      setErro(e instanceof ErroApi ? e.message : 'Não foi possível exportar.')
    } finally {
      setGerando(null)
    }
  }

  return (
    <div className="exportar">
      <div className="exportar-acoes" ref={raiz}>
        <button
          type="button" className="btn" aria-haspopup="menu" aria-expanded={aberto}
          disabled={gerando !== null} onClick={() => setAberto((v) => !v)}
        >
          {gerando ? 'Gerando…' : 'Exportar ▾'}
        </button>
        {aberto && (
          <div className="exportar-menu" role="menu">
            {FORMATOS.map((f) => (
              <button
                key={f.formato} type="button" role="menuitem" className="exportar-item"
                onClick={() => void exportar(f.formato)}
              >
                {f.rotulo}
              </button>
            ))}
          </div>
        )}
      </div>
      {erro && <p role="alert" className={classeTexto('ruim')}>{erro}</p>}
    </div>
  )
}
