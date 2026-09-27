/**
 * Captura material de MARKETING contra o sistema de verdade: vídeo de cada
 * cena e print de cada beat.
 *
 * O README não embute print — este script existe só para gravar o que se
 * mostra a quem não conhece o sistema, e por isso tem pausas deliberadas,
 * digitação em velocidade humana e uma cena por arquivo, já cortada.
 *
 * A espera fixa aqui NÃO viola o ADR-0033 §9: aquilo é regra de teste, onde
 * espera por tempo esconde corrida. Isto é gravação — a pausa é o tempo que o
 * olho de quem assiste precisa para ler a tela.
 *
 * Exige `make up` (porta 5173) e o modelo configurado: a cena do assistente é
 * a tese do produto, e sem modelo ela não acontece.
 *
 *   cd web && npx tsx scripts/capturar-marketing.ts
 *   CENAS=03-assistente npx tsx scripts/capturar-marketing.ts   # só uma cena
 */
import { mkdir, rm } from 'node:fs/promises'
import { chromium, type Browser, type Page } from '@playwright/test'

const ALVO = process.env.CAPTURA_URL ?? 'http://localhost:5173'
const SAIDA = process.env.MARKETING_SAIDA ?? new URL('../../docs/marketing/midia/', import.meta.url).pathname
const VIDEO = `${SAIDA}/video`
const PRINT = `${SAIDA}/prints`

/** 16:10. O vídeo sai neste tamanho e depois vira 9:16 e 16:9 no ffmpeg. */
const JANELA = { width: 1440, height: 900 }

/** Só as cenas pedidas, quando `CENAS` vem preenchido. */
const FILTRO = (process.env.CENAS ?? '').split(',').filter(Boolean)

type Beat = { cena: string; nome: string; em: number }
const beats: Beat[] = []
let t0 = 0

/** Pausa para o olho acompanhar — a unidade é o tempo de leitura, não o do sistema. */
const respira = (page: Page, ms: number): Promise<void> => page.waitForTimeout(ms)

/** Marca o instante de um corte, relativo ao começo da cena. */
function beat(cena: string, nome: string): void {
  const em = (Date.now() - t0) / 1000
  beats.push({ cena, nome, em })
  console.log(`    ${em.toFixed(1).padStart(6)}s  ${nome}`)
}

async function foto(page: Page, nome: string): Promise<void> {
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: `${PRINT}/${nome}.png` })
}

async function entrar(page: Page, nome: string): Promise<void> {
  await page.goto(ALVO)
  await page.getByRole('button', { name: new RegExp(nome) }).click()
  await page.getByRole('button', { name: 'Navegação' }).waitFor()
}

async function painel(page: Page, rotulo: string, ligado: boolean): Promise<void> {
  const botao = page.getByRole('button', { name: rotulo })
  if ((await botao.getAttribute('aria-pressed')) !== String(ligado)) await botao.click()
}

/**
 * Uma composição descartável, ANTES de gravar.
 *
 * A primeira chamada carrega 4,7 GB de modelo na memória do Ollama e estoura —
 * volta 422 (`invalido`), a interface mostra erro e a gravação espera um cartão
 * que nunca vem. Foi exatamente assim que a primeira tentativa se perdeu.
 * Quente, o mesmo modelo responde em ~4 s, e é esse o tempo que interessa
 * mostrar: o frio é problema de infraestrutura, não do produto.
 */
async function aquecer(browser: Browser): Promise<void> {
  console.log('\n· aquecendo o modelo (fora da gravação)')
  const ctx = await browser.newContext({ viewport: JANELA })
  const page = await ctx.newPage()
  const inicio = Date.now()
  try {
    await entrar(page, 'Cleide Ramos')
    await page.getByPlaceholder('o que está vencendo?').fill('o que está vencendo')
    await page.locator('.compositor-enviar').click()
    await page.locator('.cartao').first().waitFor({ timeout: 600_000 })
    console.log(`  ✓ quente em ${((Date.now() - inicio) / 1000).toFixed(0)}s`)
  } catch {
    console.log('  ! o aquecimento falhou — a cena do assistente vai tentar mesmo assim')
  } finally {
    await ctx.close()
  }
}

/**
 * Espera a composição aparecer, mas desiste no instante em que a interface
 * mostra erro. Sem isso, um erro do modelo vira dez minutos de espera e um
 * vídeo inútil no fim.
 */
async function esperarComposicao(page: Page): Promise<void> {
  const cartao = page.locator('.cartao').first()
  const erro = page.locator('.msg-erro')
  const falhou = erro.waitFor({ timeout: 180_000 }).then(async () => {
    throw new Error(`o assistente devolveu erro: ${await erro.innerText()}`)
  })
  falhou.catch(() => undefined)
  await Promise.race([cartao.waitFor({ timeout: 180_000 }), falhou])
}

/**
 * Uma cena = um contexto = um arquivo de vídeo. Separar assim evita depender
 * de corte por timestamp para o essencial: o corte fino do ffmpeg fica só
 * para os beats DENTRO da cena.
 */
async function cena(browser: Browser, nome: string, roteiro: (p: Page) => Promise<void>): Promise<void> {
  if (FILTRO.length > 0 && !FILTRO.includes(nome)) return
  console.log(`\n▶ ${nome}`)
  const ctx = await browser.newContext({
    viewport: JANELA,
    deviceScaleFactor: 2,
    recordVideo: { dir: `${VIDEO}/bruto`, size: JANELA },
  })
  const page = await ctx.newPage()
  t0 = Date.now()
  try {
    await roteiro(page)
  } finally {
    const video = page.video()
    await ctx.close()
    if (video) await video.saveAs(`${VIDEO}/${nome}.webm`)
    console.log(`  ✓ ${nome}.webm`)
  }
}

async function main(): Promise<void> {
  await mkdir(VIDEO, { recursive: true })
  await mkdir(PRINT, { recursive: true })
  const browser = await chromium.launch()
  if (FILTRO.length === 0 || FILTRO.includes('03-assistente')) await aquecer(browser)

  // 1. Quem entra é uma PESSOA com um cargo. O cargo é o que decide a tela.
  await cena(browser, '01-entrada', async (page) => {
    await page.goto(ALVO)
    await respira(page, 2000)
    await foto(page, '01a-entrada')
    beat('01', 'tela de entrada')
    await page.getByRole('button', { name: /Cleide Ramos/ }).hover()
    await respira(page, 900)
    await page.getByRole('button', { name: /Cleide Ramos/ }).click()
    await page.getByRole('button', { name: 'Navegação' }).waitFor()
    beat('01', 'dentro, como Cleide')
    await respira(page, 2500)
    await foto(page, '01b-dentro')
  })

  // 2. O menu convencional existe. O assistente NÃO substitui a navegação —
  //    essa é a resposta à objeção "então virou chatbot?".
  await cena(browser, '02-menu', async (page) => {
    await entrar(page, 'Cleide Ramos')
    await painel(page, 'Navegação', true)
    await respira(page, 2200)
    beat('02', 'menu de Cleide — só o que o cargo dela alcança')
    await foto(page, '02a-menu-cleide')
    await page.goto(`${ALVO}/vencimento`)
    await respira(page, 3000)
    beat('02', 'fila de vencimento pela rota tradicional')
    await foto(page, '02b-vencimento')
  })

  // 3. A TESE. A pergunta em português vira composição de componentes
  //    registrados. Com modelo local a primeira chamada leva minutos: a espera
  //    é pelo ESTADO, e o tempo real fica no log para o corte no ffmpeg.
  await cena(browser, '03-assistente', async (page) => {
    await entrar(page, 'Cleide Ramos')
    await painel(page, 'Assistente', true)
    await respira(page, 1500)
    beat('03', 'painel do assistente aberto')
    const campo = page.getByPlaceholder('o que está vencendo?')
    await campo.click()
    await campo.pressSequentially('o que está vencendo nos próximos 90 dias', { delay: 55 })
    beat('03', 'pergunta digitada')
    await respira(page, 1200)
    await foto(page, '03a-pergunta')
    const inicio = Date.now()
    await page.locator('.compositor-enviar').click()
    beat('03', 'enviada — daqui até o cartão, acelerar no corte')
    await esperarComposicao(page)
    console.log(`    modelo respondeu em ${((Date.now() - inicio) / 1000).toFixed(0)}s`)
    beat('03', 'a tela existe')
    await respira(page, 3500)
    await foto(page, '03b-composicao')

    await page.getByRole('button', { name: 'ao workspace' }).click()
    await respira(page, 3000)
    beat('03', 'promovida a tela inteira')
    await foto(page, '03c-workspace')

    // O Execution Trace NAO entra: aberto sobre o workspace, o botao "Exportar"
    // da view renderiza por cima do conteudo do painel. E o material mais forte
    // que existe para publico de desenvolvedor, e volta aqui quando isso for
    // corrigido — filmar defeito de layout entrega o defeito, nao o argumento.
  })

  // 4. Favoritar: a tela vira item do menu DELA. O usuário monta o próprio menu.
  await cena(browser, '04-fixar', async (page) => {
    await entrar(page, 'Helena Prado')
    await page.goto(`${ALVO}/vencimento`)
    await respira(page, 2200)
    const estrela = page.getByRole('button', { name: 'Fixar view' })
    await estrela.hover()
    await respira(page, 800)
    await estrela.click()
    beat('04', 'estrela — fixada')
    await respira(page, 1200)
    await painel(page, 'Fixadas', true)
    await respira(page, 2800)
    beat('04', 'o menu que ela mesma montou')
    await foto(page, '04a-fixadas')
  })

  // 5. Compartilhar por dentro: a lista só traz quem consegue abrir ESTA
  //    composição. Compartilhar aponta para uma view, não concede acesso.
  await cena(browser, '05-compartilhar', async (page) => {
    await entrar(page, 'Helena Prado')
    await page.goto(`${ALVO}/vencimento`)
    await respira(page, 1800)
    await page.getByRole('button', { name: /Compartilhar/ }).click()
    await page.getByRole('dialog', { name: 'Compartilhar view' }).waitFor()
    await respira(page, 3000)
    beat('05', 'a lista é só de quem consegue abrir')
    await foto(page, '05a-dialogo')
    await page.locator('.destinatario').first().click()
    await respira(page, 900)
    const msg = page.locator('#msg')
    await msg.click()
    await msg.pressSequentially('confere esse lote antes de sexta', { delay: 55 })
    await respira(page, 900)
    beat('05', 'mensagem escrita')
    await page.getByRole('button', { name: 'Enviar' }).click()
    await page.getByText('Entregue na caixa de quem você escolheu').waitFor({ timeout: 20_000 })
    beat('05', 'entregue — e ela abre sob a permissão dela')
    await respira(page, 3200)
    await foto(page, '05b-entregue')
  })

  // 6. O contraste que prova a arquitetura: a mesma rota, duas identidades.
  //    Não é botão cinza — para Ivo a ação não foi montada.
  await cena(browser, '06-permissao', async (page) => {
    await entrar(page, 'Helena Prado')
    await painel(page, 'Navegação', true)
    await respira(page, 1500)
    await foto(page, '06a-menu-helena')
    await page.goto(`${ALVO}/quarentena`)
    await respira(page, 3500)
    beat('06', 'Helena, RT — a quarentena com a ação')
    await foto(page, '06b-helena-quarentena')

    await page.context().clearCookies()
    await entrar(page, 'Ivo Nakamura')
    await painel(page, 'Navegação', true)
    await respira(page, 1500)
    beat('06', 'Ivo, gerente — o menu já é outro')
    await foto(page, '06c-menu-ivo')
    await page.goto(`${ALVO}/quarentena`)
    await respira(page, 3500)
    beat('06', 'mesma URL, e a ação não existe para ele')
    await foto(page, '06d-ivo-quarentena')
  })

  // 7. Tema escuro: o mesmo sistema, para o post que precisa de contraste.
  await cena(browser, '07-escuro', async (page) => {
    await entrar(page, 'Marco Bertoni')
    await page.getByRole('button', { name: 'Usar tema escuro' }).click()
    await respira(page, 1200)
    await page.goto(`${ALVO}/lotes`)
    await respira(page, 3000)
    beat('07', 'lotes, tema escuro')
    await foto(page, '07a-lotes-escuro')
    await painel(page, 'Navegação', true)
    await respira(page, 2000)
    await foto(page, '07b-menu-escuro')
  })

  await browser.close()
  await rm(`${VIDEO}/bruto`, { recursive: true, force: true })

  console.log('\n— cortes, em segundos desde o início de cada cena —')
  for (const b of beats) console.log(`${b.cena}  ${b.em.toFixed(1).padStart(7)}s  ${b.nome}`)
  console.log(`\nvídeo: ${VIDEO}\nprints: ${PRINT}`)
}

await main()
