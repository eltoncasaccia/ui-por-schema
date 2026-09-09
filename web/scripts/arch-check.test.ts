/**
 * T-005 AC-1 — o verificador quebrado de propósito, uma regra por vez.
 *
 * A regra da casa: *uma regra que nunca falhou não é evidência de nada.* Um
 * `arch-check` que sai com código 0 pode estar limpo — ou pode estar lendo o
 * diretório errado, com um `alvo()` que nunca casa. Os dois são verdes.
 *
 * Cada teste aqui aponta o verificador para uma fixture que viola **uma** regra
 * e afirma que ele acusa **aquela** regra. É o par do
 * `tests/arquitetura/test_verificador_falha_quando_violado.py`, do lado Python.
 */
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { REGRAS, formatar, verificar } from './arch-check'

const FIXTURES = join(import.meta.dirname, 'fixtures-violacao')
const FONTE = join(import.meta.dirname, '..', 'src')

const violadas = (raiz: string) => new Set(verificar(raiz).map((v) => v.regra))

describe('arch-check · o verificador acusa cada violação', () => {
  // --- AC-1, regra a regra ------------------------------------------------
  const casos: [number, string][] = [
    [7, 'view importando query/ ou o cliente de API'],
    [8, 'view com useEffect'],
    [9, 'view importando @tanstack/react-query'],
    [10, 'view com dangerouslySetInnerHTML'],
    [11, 'arquivo em generated/ sem o cabeçalho de gerado'],
    [12, 'string de conexão de banco no cliente'],
  ]

  for (const [numero, descricao] of casos) {
    it(`regra ${numero} · ${descricao}`, () => {
      expect(violadas(FIXTURES), `a regra ${numero} não acusou`).toContain(numero)
    })
  }

  // --- AC-2 ---------------------------------------------------------------
  it('AC-2 · o código real sai limpo', () => {
    const achadas = verificar(FONTE)
    expect(formatar(achadas)).toBe('')
  })

  it('as seis regras da T-005 estão implementadas', () => {
    expect(REGRAS.map((r) => r.numero)).toEqual([7, 8, 9, 10, 11, 12])
  })

  // --- AC-3 ---------------------------------------------------------------
  it('AC-3 · a saída nomeia arquivo, linha e regra', () => {
    const [primeira] = verificar(FIXTURES)
    expect(primeira).toBeDefined()
    expect(primeira!.arquivo).toMatch(/\.tsx?$/)
    expect(primeira!.linha).toBeGreaterThan(0)
    expect(primeira!.nome.length).toBeGreaterThan(10)
    expect(formatar([primeira!])).toContain(`:${primeira!.linha}`)
  })

  // --- AC-4 ---------------------------------------------------------------
  it('AC-4 · roda em menos de 5 s', () => {
    const inicio = Date.now()
    verificar(FONTE)
    // Verificador lento é verificador que ninguém roda antes de commitar.
    expect(Date.now() - inicio).toBeLessThan(5000)
  })

  // --- o teste que impede o verde por cegueira ----------------------------
  it('não acusa regra em arquivo que ela não alcança', () => {
    /**
     * `useEffect` em `shell/` é legítimo — a moldura tem ciclo de vida; a view
     * é que não tem. Se o `alvo()` da regra 8 casasse com tudo, ela acusaria
     * aqui, e a suíte ficaria vermelha por uma regra que não existe.
     */
    const doShell = verificar(FONTE).filter((v) => v.arquivo.startsWith('shell/'))
    expect(doShell).toEqual([])
  })
})
