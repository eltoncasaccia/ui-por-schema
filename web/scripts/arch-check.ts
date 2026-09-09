/**
 * Verificador de arquitetura do lado TypeScript. T-005, regras 7 a 12.
 *
 * O par do `import-linter` do `api/`. Enquanto ele não existiu, as fronteiras do
 * cliente eram convenção — e o `make check` inteiro parava aqui, porque o
 * Makefile já o invocava (achado A-13).
 *
 * **Análise por texto, e não por AST, de propósito.** O AC-4 da T-005 pede menos
 * de 5 s: verificador lento é verificador que ninguém roda antes de commitar, e
 * aí a regra volta a valer só na revisão. As seis regras são todas sobre
 * *presença* de um símbolo ou de um import, e para isso texto basta. O preço é
 * o falso positivo em comentário, e ele é aceito — comentar `useEffect` numa
 * view é raro, e o ruído é barato perto de carregar um parser.
 *
 * `verificar()` recebe a raiz como parâmetro. É isso que permite o
 * `arch-check.test.ts` apontar para fixtures com violação de propósito e
 * afirmar que o verificador quebra. Uma regra que nunca falhou não é evidência
 * de nada.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

export type Violacao = {
  regra: number
  nome: string
  arquivo: string
  linha: number
  trecho: string
}

type Regra = {
  numero: number
  nome: string
  /** Onde a regra vale. Caminho relativo à raiz, com `/`. */
  alvo: (caminhoRelativo: string) => boolean
  /** O que a regra proíbe, linha a linha. */
  proibido: RegExp
  adr: string
}

const ehView = (p: string) => p.startsWith('views/') && p.endsWith('.tsx')

export const REGRAS: Regra[] = [
  {
    numero: 7,
    nome: 'view não busca dado: proibido importar query/ ou o cliente de API',
    alvo: ehView,
    proibido: /from\s+['"][^'"]*(\.\.\/query\/|\.\.\/api|generated\/api)/,
    adr: 'ADR-0007',
  },
  {
    numero: 8,
    nome: 'view não contém useEffect',
    alvo: ehView,
    // View que busca, sincroniza ou agenda deixou de ser função do viewmodel e
    // virou componente com vida própria.
    proibido: /\buseEffect\s*\(/,
    adr: 'ADR-0007',
  },
  {
    numero: 9,
    nome: 'view não importa @tanstack/react-query',
    alvo: ehView,
    proibido: /from\s+['"]@tanstack\/react-query['"]/,
    adr: 'ADR-0008',
  },
  {
    numero: 10,
    nome: 'view não usa dangerouslySetInnerHTML',
    // O schema vem de um modelo de linguagem. Injetar HTML a partir dele é
    // entregar execução ao conteúdo que o ADR-0012 trata como hostil.
    alvo: ehView,
    proibido: /dangerouslySetInnerHTML/,
    adr: 'ADR-0001',
  },
  {
    numero: 11,
    nome: 'arquivo gerado perdeu o cabeçalho de GERADO — foi editado à mão?',
    alvo: (p) => p.startsWith('generated/') && (p.endsWith('.ts') || p.endsWith('.tsx')),
    // Regra invertida: aqui o "proibido" é a AUSÊNCIA, tratada em `analisar`.
    proibido: /(?!)/,
    adr: 'ADR-0017',
  },
  {
    numero: 12,
    nome: 'string de conexão de banco no cliente',
    // ADR-0018: o Postgres é acessado SÓ pela API. Uma string dessas no bundle
    // significa que alguém tentou o atalho.
    alvo: (p) => p.endsWith('.ts') || p.endsWith('.tsx'),
    proibido: /postgres(ql)?:\/\//,
    adr: 'ADR-0018',
  },
]

/** Marca que todo arquivo de `generated/` carrega. Ver `scripts/gerar-tipos.ts`. */
const MARCA_GERADO = /GERADO|@generated|NÃO EDITE|NAO EDITE/

function arquivos(raiz: string): string[] {
  const achados: string[] = []
  const andar = (dir: string) => {
    for (const nome of readdirSync(dir)) {
      if (nome === 'node_modules' || nome === '.git') continue
      const cheio = join(dir, nome)
      if (statSync(cheio).isDirectory()) andar(cheio)
      else if (/\.tsx?$/.test(nome)) achados.push(cheio)
    }
  }
  andar(raiz)
  return achados.sort()
}

export function verificar(raiz: string): Violacao[] {
  const violacoes: Violacao[] = []

  for (const cheio of arquivos(raiz)) {
    const rel = relative(raiz, cheio).split('\\').join('/')
    const texto = readFileSync(cheio, 'utf8')
    const linhas = texto.split('\n')

    for (const regra of REGRAS) {
      if (!regra.alvo(rel)) continue

      // Regra 11 é sobre ausência: o arquivo gerado tem de se declarar gerado.
      if (regra.numero === 11) {
        if (!MARCA_GERADO.test(texto)) {
          violacoes.push({
            regra: 11,
            nome: regra.nome,
            arquivo: rel,
            linha: 1,
            trecho: linhas[0]?.slice(0, 60) ?? '',
          })
        }
        continue
      }

      linhas.forEach((linha, i) => {
        if (regra.proibido.test(linha)) {
          violacoes.push({
            regra: regra.numero,
            nome: regra.nome,
            arquivo: rel,
            linha: i + 1,
            trecho: linha.trim().slice(0, 80),
          })
        }
      })
    }
  }
  return violacoes
}

export function formatar(violacoes: Violacao[]): string {
  // AC-3: arquivo, linha e regra. Sem os três, a saída obriga a caçar.
  return violacoes
    .map((v) => `${v.arquivo}:${v.linha}  regra ${v.regra} — ${v.nome}\n    ${v.trecho}`)
    .join('\n')
}

if (process.argv[1]?.endsWith('arch-check.ts')) {
  const raiz = join(import.meta.dirname, '..', 'src')
  const inicio = Date.now()
  const violacoes = verificar(raiz)
  const ms = Date.now() - inicio

  if (violacoes.length > 0) {
    console.error(formatar(violacoes))
    console.error(`\n${violacoes.length} violação(ões) de arquitetura. ${ms} ms`)
    process.exit(1)
  }
  console.log(`arch-check: ${REGRAS.length} regras, nenhuma violação. ${ms} ms`)
}
