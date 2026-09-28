/**
 * Quantos blocos o modelo em uso compõe, por pergunta.
 *
 * Resultado e leitura: `docs/marketing/README.md` §2.
 *
 * A pergunta de marketing não é "o schema é válido" (a R-001 já mediu isso) —
 * é "a tela que nasce tem substância?". Uma composição de um bloco só é
 * correta e pobre de filmar; três blocos nascendo em sequência é o produto.
 */
import { chromium } from '@playwright/test'

const ALVO = process.env.CAPTURA_URL ?? 'http://localhost:5173'

const PERGUNTAS = [
  'o que está vencendo nos próximos 90 dias',
  'quero ver o gráfico de vencimentos por mês e a fila de lotes vencendo',
  'me mostra a situação do estoque: o que vence, o que está parado em quarentena e o saldo por unidade',
  'houve excursão de temperatura no refrigerado?',
]

const browser = await chromium.launch()
const ctx = await browser.newContext()
const page = await ctx.newPage()
await page.goto(ALVO)
await page.getByRole('button', { name: /Cleide Ramos/ }).click()
await page.getByRole('button', { name: 'Navegação' }).waitFor()

type Trace = { modelo: string; ms_total: number; schema_valido: boolean; aceitos: string[]; rejeitados: string[] }
type Corpo = { ok: boolean; dados?: { blocos: { tipo: string }[] }; meta?: { trace: Trace }; erro?: { mensagem: string } }

for (const pergunta of PERGUNTAS) {
  const r = await page.evaluate(async (p: string) => {
    const csrf = document.cookie.split('; ').find((c) => c.startsWith('csrf='))?.slice(5) ?? ''
    const resp = await fetch('/api/assistente/compor', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify({ pergunta: p }),
    })
    return (await resp.json()) as unknown
  }, pergunta)
  const c = r as Corpo
  if (!c.ok) { console.log(`✗ ${pergunta}\n   ${c.erro?.mensagem}`); continue }
  const t = c.meta?.trace
  console.log(`\n· ${pergunta}`)
  console.log(`  blocos     ${c.dados?.blocos.map((b) => b.tipo).join(' + ') ?? '—'}`)
  console.log(`  aceitos    ${t?.aceitos.join(', ')}   rejeitados: ${t?.rejeitados.join(', ') || 'nenhum'}`)
  console.log(`  tempo      ${t?.ms_total} ms   schema válido: ${t?.schema_valido}`)
}

await browser.close()
