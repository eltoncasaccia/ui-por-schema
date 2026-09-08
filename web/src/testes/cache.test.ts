/**
 * A regra do ADR-0008, verificada no código-fonte.
 *
 * Bug real: a caixa de recebidas estava chaveada como `['recebidas']`, sem o
 * ator. Sair de um usuário e entrar com outro servia a caixa do anterior — a
 * pessoa via um compartilhamento que não era dela.
 *
 * O ADR já dizia "a identidade do ator entra na queryKey, obrigatoriamente".
 * Eu escrevi a regra e violei em dois lugares, e nenhum teste percebeu. Este
 * teste é genérico de propósito: pega o próximo esquecimento, não só estes.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const RAIZ = join(import.meta.dirname, '..')

function arquivos(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n)
    if (statSync(p).isDirectory()) return n === 'testes' ? [] : arquivos(p)
    return /\.tsx?$/.test(n) ? [p] : []
  })
}

/** Extrai o conteúdo de cada `queryKey: [...]` do fonte. */
function chaves(src: string): string[] {
  return [...src.matchAll(/queryKey:\s*\[([^\]]*)\]/g)].map((m) => m[1]!.trim())
}

describe('cache nunca cruza usuários', () => {
  const fontes = arquivos(RAIZ).map((p) => [p, readFileSync(p, 'utf8')] as const)

  it('toda queryKey começa pela identidade do ator', () => {
    const faltando: string[] = []
    for (const [p, src] of fontes) {
      for (const k of chaves(src)) {
        const primeiro = k.split(',')[0]!.trim()
        // Aceita `eu.id`, `atorId`, ou qualquer coisa que nomeie o ator.
        if (!/^(eu\.id|atorId|ator\.id)$/.test(primeiro)) {
          faltando.push(`${p.replace(RAIZ, '')}: [${k}]`)
        }
      }
    }
    expect(faltando, 'queryKey sem o ator serve dado de outra pessoa').toEqual([])
  })

  it('existem queryKeys para o teste ter o que verificar', () => {
    const total = fontes.flatMap(([, s]) => chaves(s)).length
    expect(total).toBeGreaterThan(3)
  })

  it('o logout limpa o cache — segunda camada', () => {
    const app = readFileSync(join(RAIZ, 'App.tsx'), 'utf8')
    expect(app).toContain('limparAoSair()')
    const cache = readFileSync(join(RAIZ, 'estado', 'cache.ts'), 'utf8')
    expect(cache).toContain('cache.clear()')
  })
})
