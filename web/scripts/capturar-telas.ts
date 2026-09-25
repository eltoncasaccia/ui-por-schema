/**
 * Captura as telas que o README publica, contra o sistema de verdade.
 *
 * Existe para o print não envelhecer em silêncio: quem muda a interface roda
 * `make capturas` e as imagens acompanham o código, em vez de mostrarem uma
 * versão que não existe mais.
 *
 * Usa o stack de desenvolvimento (`make up`, porta 5173) porque as telas do
 * assistente só fazem sentido com um modelo configurado — o e2e sobe SEM chave
 * de provedor de propósito (ADR-0013), e por isso não serve aqui.
 */
import { mkdir } from 'node:fs/promises'
import { chromium, type Page } from '@playwright/test'

const ALVO = process.env.CAPTURA_URL ?? 'http://localhost:5173'
const DESTINO = new URL('../../docs/imagens/', import.meta.url).pathname

/** 16:10 em 1x: legível no GitHub sem pesar o repositório. */
const JANELA = { width: 1440, height: 900 }

async function entrar(page: Page, nome: string): Promise<void> {
  await page.goto(ALVO)
  await page.getByRole('button', { name: new RegExp(nome) }).click()
  await page.getByRole('button', { name: 'Navegação' }).waitFor()
}

async function painel(page: Page, rotulo: string, ligado: boolean): Promise<void> {
  const botao = page.getByRole('button', { name: rotulo })
  if ((await botao.getAttribute('aria-pressed')) !== String(ligado)) await botao.click()
}

async function foto(page: Page, nome: string): Promise<void> {
  // `networkidle` em vez de espera fixa: a tela só é fotografada depois de o
  // último `dados` responder, senão o print sai com o esqueleto de carregamento.
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: `${DESTINO}${nome}.png` })
  console.log(`  ✓ ${nome}.png`)
}

async function main(): Promise<void> {
  await mkdir(DESTINO, { recursive: true })
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: JANELA, deviceScaleFactor: 1 })
  const page = await ctx.newPage()

  console.log('entrada')
  await page.goto(ALVO)
  await foto(page, '01-entrada')

  console.log('Cleide — conferente')
  await entrar(page, 'Cleide Ramos')
  await painel(page, 'Navegação', true)
  await foto(page, '02-menu-cleide')

  await page.goto(`${ALVO}/vencimento`)
  await foto(page, '03-vencimento')

  // A TESE, em duas telas: a pergunta em português vira composição de
  // componentes registrados. O modelo é local (Ollama), e com o catálogo de 24
  // componentes a primeira chamada leva minutos — por isso a espera é longa e
  // pelo ESTADO, nunca por tempo fixo.
  console.log('assistente — a composição (modelo local, pode levar minutos)')
  await page.goto(ALVO)
  await painel(page, 'Assistente', true)
  await page.getByPlaceholder('o que está vencendo?').fill('o que está vencendo nos próximos 90 dias')
  const t0 = Date.now()
  await page.locator('.compositor-enviar').click()
  // O bloco nasce DENTRO do painel do assistente, com o botão "ao workspace"
  // ao lado — não no workspace. Esperar por `main .cartao` aqui expira sempre.
  await page.locator('.cartao').first().waitFor({ timeout: 600_000 })
  console.log(`  modelo respondeu em ${((Date.now() - t0) / 1000).toFixed(0)}s`)
  await foto(page, '04-assistente')

  // O mesmo bloco, promovido à tela inteira: é o mesmo componente que a rota
  // tradicional abre, e o mesmo motor de render (ADR-0005).
  await page.getByRole('button', { name: 'ao workspace' }).click()
  await foto(page, '05-workspace')

  await painel(page, 'Execution Trace', true)
  await foto(page, '06-trace')

  console.log('Helena — RT')
  await ctx.clearCookies()
  await entrar(page, 'Helena Prado')
  await painel(page, 'Navegação', true)
  await foto(page, '07-menu-helena')
  await page.goto(`${ALVO}/quarentena`)
  await foto(page, '08-quarentena')

  console.log('Marco — diretor')
  await ctx.clearCookies()
  await entrar(page, 'Marco Bertoni')
  await page.goto(`${ALVO}/lotes`)
  await foto(page, '09-lotes')

  await browser.close()
}

await main()
