import { expect, test, type Page } from '@playwright/test'
import { entrar, lerComponente } from './apoio'

/**
 * Recebimento pelo navegador — o fluxo que o [A-53](../../docs/tasks/ACHADOS.md)
 * mostrou estar morto e que a `TelaRecebimento.tsx` religou.
 *
 * Este arquivo nasceu como experimento sobre a regra do e2e
 * ([A-004](../../docs/relatorios/A-004-e2e-vale-a-pena.md)). Os 12 testes de
 * `recebimento_registrar.test.tsx` passavam entregando `vm.lido` pronto ao
 * componente: provavam que o formulário **desenha** certo o produto lido, e
 * nunca que alguém conseguia lê-lo. O primeiro teste contra o servidor de
 * verdade derrubou a tela inteira.
 *
 * Por isso o primeiro teste aqui afirma a PONTE — do código digitado até o
 * produto na tela — e não o desenho, que já está coberto.
 */
interface VMRecebimento {
  lido?: { ean: string; nome: string } | null
  ean_nao_encontrado?: string | null
}
interface VMLista {
  total: number
}

/** Losartana Potássica 50mg, classe `comum` — existe no seed, com este EAN. */
const EAN = '7891234000011'

function emDias(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

/**
 * O que o leitor USB faz: digita e aperta Enter. Nenhum clique.
 *
 * Espera o produto RESOLVER antes de devolver. Sem isso o teste corre na
 * frente do servidor e o Enter seguinte cai num `vm.lido` ainda nulo — foi
 * assim que a primeira versão destes testes acusou defeito onde não havia.
 */
async function bipar(page: Page): Promise<void> {
  const campo = page.getByLabel('Código de barras do produto')
  await campo.fill(EAN)
  await campo.press('Enter')
  await expect(page.getByRole('button', { name: /^Acrescentar / })).toBeVisible()
}

test.describe('recebimento', () => {
  test('A-53 · o código lido resolve o produto no servidor', async ({ page }) => {
    await entrar(page, 'cleide')

    // O servidor sempre soube resolver o EAN quando recebia o param: o furo
    // estava entre a tela e ele.
    const porParam = await lerComponente<VMRecebimento>(page, 'recebimento_registrar', {
      ean: EAN,
    })
    expect(porParam.lido?.ean).toBe(EAN)

    await page.goto('/recebimento/novo')

    // A ponte: `bipar` só volta quando o botão existe, e ele só existe se
    // `vm.lido` chegou — o que exige alguém ter repedido o componente com o
    // código digitado. Antes do A-53, ninguém repedia.
    await bipar(page)
  })

  test('o segundo Enter acrescenta o item, sem tirar a mão do teclado', async ({ page }) => {
    // `RNF-02`: a tela existe para ser usada com as duas mãos ocupadas. Se o
    // laço exigisse clique a cada caixa, a tela funcionaria e serviria mal.
    await entrar(page, 'cleide')
    await page.goto('/recebimento/novo')
    await bipar(page)

    await page.getByLabel('Código de barras do produto').press('Enter')
    await expect(page.getByLabel(/^Número do lote de /)).toBeVisible()
  })

  test('um recebimento completo grava, em clique real', async ({ page }) => {
    await entrar(page, 'cleide')
    const antes = await lerComponente<VMLista>(page, 'recebimento_lista')

    await page.goto('/recebimento/novo')
    await bipar(page)
    await page.getByRole('button', { name: /^Acrescentar / }).click()

    const carimbo = Date.now()
    await page.getByLabel('Nota fiscal').fill(`NF-E2E-${carimbo}`)
    await page.getByLabel('Fornecedor').fill('Distribuidora Teste')
    await page.getByLabel(/^Número do lote de /).fill(`L-E2E-${carimbo % 100000}`)
    await page.getByLabel(/^Fabricação de /).fill(emDias(-60))
    await page.getByLabel(/^Validade de /).fill(emDias(400))
    await page.getByLabel(/^Quantidade física de /).fill('10')

    const confirmar = page.getByRole('button', { name: 'Confirmar recebimento' })
    await expect(confirmar).toBeEnabled()
    await confirmar.click()
    await page.getByRole('button', { name: 'Confirmar', exact: true }).click()

    await expect(page.getByText('Entrada invalida.')).toHaveCount(0)

    // A prova é a lista crescer, lida de novo pela API — não a mensagem na
    // tela. Foi uma asserção fraca que escondeu o A-52.
    await expect
      .poll(async () => (await lerComponente<VMLista>(page, 'recebimento_lista')).total, {
        message: 'o recebimento gravado deveria aparecer na lista',
      })
      .toBe(antes.total + 1)
  })

  test('(negativo) código que não existe avisa, e não acrescenta nada', async ({ page }) => {
    await entrar(page, 'cleide')
    await page.goto('/recebimento/novo')

    const campo = page.getByLabel('Código de barras do produto')
    await campo.fill('0000000000000')
    await campo.press('Enter')

    await expect(page.getByText(/Nenhum produto com o código/)).toBeVisible()
    await expect(page.getByRole('button', { name: /^Acrescentar / })).toHaveCount(0)
  })
})
