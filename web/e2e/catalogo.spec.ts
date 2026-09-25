import { expect, test } from '@playwright/test'
import { abrirNavegacao, entrar, itemDoMenu, lerComponente } from './apoio'

interface FilaQuarentena {
  total: number
  linhas: { lote_id: string; numero: string; produto: string }[]
}

/**
 * AC-3 e AC-4 da T-053 — os dois negativos que provam o ADR-0003 no navegador.
 *
 * O AC-3 é sobre o MENU; o AC-4 é sobre o SERVIDOR. A diferença é a tese: menu
 * escondido é conveniência, e quem protege é a autorização que roda no `load`
 * com a identidade real (ADR-0004). Por isso o AC-4 digita a URL.
 */
test.describe('catálogo por ator', () => {
  test('AC-3 · Helena vê "Liberar quarentena" no menu', async ({ page }) => {
    await entrar(page, 'helena')
    await abrirNavegacao(page)
    await expect(itemDoMenu(page, 'Liberar quarentena')).toBeVisible()
  })

  test('AC-3 · Cleide NÃO vê, embora leia lote', async ({ page }) => {
    await entrar(page, 'cleide')
    await abrirNavegacao(page)

    // O controle do negativo: ela vê "Lotes", então o menu carregou e o
    // catálogo dela chegou. A ausência do outro item é filtro, não tela vazia.
    await expect(itemDoMenu(page, 'Lotes')).toBeVisible()
    await expect(itemDoMenu(page, 'Liberar quarentena')).toHaveCount(0)
  })

  test('AC-4 · Cleide digitando a URL recebe negativa, e o lote continua em quarentena', async ({
    browser,
  }) => {
    const deHelena = await browser.newContext()
    const helena = await deHelena.newPage()
    await entrar(helena, 'helena')

    // O id vem da fila da própria RT: o teste não inventa um lote do seed.
    const antes = await lerComponente<FilaQuarentena>(helena, 'quarentena_fila')
    expect(antes.linhas.length).toBeGreaterThan(0)
    const alvo = antes.linhas[0]!

    const deCleide = await browser.newContext()
    const cleide = await deCleide.newPage()
    await entrar(cleide, 'cleide')
    await cleide.goto(`/quarentena/${alvo.lote_id}`)

    // A negativa é do servidor, e a tela mostra a mensagem DELE, palavra por
    // palavra. Um `/não|autoriza/i` casaria também com "Não foi possível
    // carregar", que é falha de rede — o oposto do que este teste prova.
    await expect(cleide.getByText('Sem acesso a este componente.')).toBeVisible()
    // E não existe caminho para liberar NA TELA: nenhum botão, nem
    // desabilitado. A busca é dentro do workspace de propósito — procurar na
    // página inteira casaria com o item "Liberar quarentena" do menu, e este
    // teste passaria a medir o menu, que é o assunto do AC-3.
    await expect(cleide.locator('main.workspace').getByRole('button', { name: /liberar/i })).toHaveCount(0)
    // Nem o número do lote vazou para quem não pode ver esta tela.
    await expect(cleide.locator('body')).not.toContainText(alvo.numero)

    // O ALVO não mudou: continua na fila, para quem pode ver. Não comparamos
    // `total` — desde a T-057, `liberacao.spec.ts` faz uma liberação de
    // verdade em paralelo, e o total da fila é estado GLOBAL, compartilhado
    // por todo o arquivo de teste. O que este teste prova é que a tentativa
    // forjada de Cleide não tocou o lote dela, não que mais ninguém escreveu.
    const depois = await lerComponente<FilaQuarentena>(helena, 'quarentena_fila')
    expect(depois.linhas.map((l) => l.lote_id)).toContain(alvo.lote_id)

    await deHelena.close()
    await deCleide.close()
  })
})
