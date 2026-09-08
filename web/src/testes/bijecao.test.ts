/**
 * T-039 · a bijeção registry ↔ views. ADR-0017, AC-1 a AC-6.
 *
 * O ADR-0017 diz, com todas as letras: *"é este teste que faz o ADR-0017 valer
 * o que o ADR-0006 valia. Sem ele, esta decisão é uma regressão."*
 *
 * E ficou sem ele. A auditoria A-002 achou os três componentes com registro e
 * view por coincidência de disciplina, não por verificação — que é exatamente
 * o modo de apodrecimento que o ADR-0006 descrevia: "existe a lista que o
 * modelo conhece e a lista que o sistema sabe renderizar; as duas divergem".
 */
import { execFileSync } from 'node:child_process'
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { IDS_DA_API, TAMANHOS, type ComponentId } from '../generated/componentes'
import { VIEWS } from '../views/indice'

const RAIZ = join(import.meta.dirname, '..')
const CONTRATO = join(RAIZ, 'generated', 'contrato.json')

/** As views são os arquivos de `views/`, tirando os que não são componente. */
function arquivosDeView(): string[] {
  return readdirSync(join(RAIZ, 'views'))
    .filter((n) => n.endsWith('.tsx'))
    .map((n) => n.replace('.tsx', ''))
    .sort()
}

describe('bijeção registry ↔ views', () => {
  // --- AC-1 ---------------------------------------------------------------
  it('AC-1 · todo id registrado na API tem uma view', () => {
    const semView = IDS_DA_API.filter((id) => !(id in VIEWS))
    expect(semView, 'componente registrado sem view quebra em runtime').toEqual([])
  })

  // --- AC-2 ---------------------------------------------------------------
  it('AC-2 · toda view corresponde a um id registrado', () => {
    const orfas = arquivosDeView().filter((v) => !(IDS_DA_API as readonly string[]).includes(v))
    expect(orfas, 'view sem registro é código morto que ninguém alcança').toEqual([])
  })

  it('AC-2 · o mapa VIEWS não tem chave a mais nem a menos', () => {
    expect(Object.keys(VIEWS).sort()).toEqual([...IDS_DA_API].sort())
  })

  // --- AC-3 ---------------------------------------------------------------
  it('AC-3 · o arquivo gerado corresponde ao contrato versionado', () => {
    const contrato = JSON.parse(readFileSync(CONTRATO, 'utf8')) as {
      componentes: { id: string; tamanho: string }[]
    }
    expect(contrato.componentes.map((c) => c.id).sort()).toEqual([...IDS_DA_API].sort())
    for (const c of contrato.componentes) {
      expect(TAMANHOS[c.id as ComponentId]).toBe(c.tamanho)
    }
  })

  it('AC-3 · o gerado é regenerável e idêntico', () => {
    // Regenera a partir do MESMO contrato e compara. Pega edição manual no
    // arquivo gerado, que é o jeito silencioso de a divergência começar.
    const antes = readFileSync(join(RAIZ, 'generated', 'componentes.ts'), 'utf8')
    execFileSync('npx', ['tsx', 'scripts/gerar-tipos.ts'], { cwd: join(RAIZ, '..') })
    const depois = readFileSync(join(RAIZ, 'generated', 'componentes.ts'), 'utf8')
    expect(depois).toBe(antes)
  })

  it('AC-3 · o gerado avisa que não deve ser editado', () => {
    const src = readFileSync(join(RAIZ, 'generated', 'componentes.ts'), 'utf8')
    expect(src.slice(0, 200)).toContain('NÃO EDITE')
  })

  // --- AC-6 ---------------------------------------------------------------
  it('AC-6 · nenhuma view declara o próprio viewmodel', () => {
    // Tipo escrito à mão continua compilando depois de a API mudar — com o
    // tipo errado. É a segunda lista que o ADR-0006 evitava.
    for (const nome of arquivosDeView()) {
      const src = readFileSync(join(RAIZ, 'views', `${nome}.tsx`), 'utf8')
      expect(src, `${nome} precisa importar o viewmodel gerado`).toContain(
        "from '../generated/componentes'",
      )
      expect(src, `${nome} não pode declarar interface VM própria`).not.toMatch(
        /export interface VM\b/,
      )
    }
  })

  it('AC-6 · o contrato de View usa o tipo gerado', () => {
    const src = readFileSync(join(RAIZ, 'views', 'tipos.ts'), 'utf8')
    expect(src).toContain('ViewModel')
    expect(src).toContain("from '../generated/componentes'")
  })
})
