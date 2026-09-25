import { expect, test } from '@playwright/test'
import { NAV_ROTAS } from '../src/app/layout/rotasOperacao'
import { abrirNavegacao, entrar, itemDoMenu, tituloDaTela, type Persona } from './apoio'

/**
 * AC-6 e AC-7 da T-053, e AC-1 da T-057.
 *
 * O AC-6 lê a tabela `ROTAS_OPERACAO` em vez de repetir os paths aqui: a
 * tabela é a fonte única que alimenta o roteador E o menu (T-031), e um teste
 * que copiasse os valores deixaria de pegar exatamente a divergência que ele
 * existe para pegar.
 *
 * **AC-1 (T-057):** o AC-6 rodava só com Marco, e o catálogo dele tem só 2 das
 * 6 rotas sem parâmetro — `/quarentena`, `/controlados`, `/saida` e
 * `/recebimento/novo` nunca tinham path e título conferidos por ninguém
 * (achado A-48). Três personas cobrem as seis; a lista esperada continua
 * derivada do catálogo de CADA UMA, nunca fixada aqui.
 */
const PERSONAS_DA_UNIAO: Persona[] = ['marco', 'helena', 'cleide']

/** As rotas do menu que o catálogo desta persona autoriza — a mesma regra do
 * `PainelNavegacao` (ADR-0003): id do componente presente, e os extras de
 * `requerTambemNoMenu` também presentes. */
function esperadasParaCatalogo(ids: ReadonlySet<string>) {
  return NAV_ROTAS.filter(
    (r) => ids.has(r.componente) && (r.requerTambemNoMenu ?? []).every((id) => ids.has(id)),
  )
}

test.describe('navegação por catálogo', () => {
  for (const quem of PERSONAS_DA_UNIAO) {
    test(`AC-1/AC-6 · ${quem}: cada rota do menu leva ao path e ao título da tabela`, async ({ page }) => {
      await entrar(page, quem)
      await abrirNavegacao(page)

      const envelope = (await (await page.request.get('/api/catalogo')).json()) as { dados: { id: string }[] }
      const ids = new Set(envelope.dados.map((c) => c.id))
      const esperadas = esperadasParaCatalogo(ids)
      expect(esperadas.length).toBeGreaterThan(0)

      // O menu mostra essas rotas e NENHUMA a mais: a contagem fecha a porta
      // para um item que aparecesse sem estar no catálogo.
      for (const rota of esperadas) {
        await expect(itemDoMenu(page, rota.rotulo)).toBeVisible()
      }
      const ausentes = NAV_ROTAS.filter((r) => !esperadas.includes(r))
      for (const rota of ausentes) {
        await expect(itemDoMenu(page, rota.rotulo)).toHaveCount(0)
      }

      for (const rota of esperadas) {
        await itemDoMenu(page, rota.rotulo).click()
        await expect(page).toHaveURL(new RegExp(`${rota.path}$`))
        await expect(tituloDaTela(page)).toHaveText(rota.rotulo)
        await expect(itemDoMenu(page, rota.rotulo)).toHaveAttribute('aria-current', 'page')
      }
    })
  }

  test('AC-1 · a união de Marco, Helena e Cleide cobre as 6 rotas sem parâmetro', async ({ browser }) => {
    const cobertas = new Set<string>()
    for (const quem of PERSONAS_DA_UNIAO) {
      const ctx = await browser.newContext()
      const p = await ctx.newPage()
      await entrar(p, quem)
      const envelope = (await (await p.request.get('/api/catalogo')).json()) as { dados: { id: string }[] }
      const ids = new Set(envelope.dados.map((c) => c.id))
      for (const rota of esperadasParaCatalogo(ids)) cobertas.add(rota.path)
      await ctx.close()
    }

    // As três juntas cobrem as seis — nem uma sobra (nenhuma das três vê uma
    // rota que não exista em `NAV_ROTAS`), nem uma falta: um componente novo
    // na tabela que nenhuma das três alcança quebra ESTE teste, não
    // silenciosamente o board, como aconteceu antes do A-48.
    expect(cobertas.size).toBe(NAV_ROTAS.length)
    for (const rota of NAV_ROTAS) expect(cobertas.has(rota.path)).toBe(true)
  })
})

test.describe('navegação do diretor', () => {
  test.beforeEach(async ({ page }) => {
    // Marco é diretor: o catálogo dele tem todas as rotas, então o menu
    // completo aparece sem filtro atrapalhar o AC-7.
    await entrar(page, 'marco')
    await abrirNavegacao(page)
  })

  test('AC-7 · o item marcado é sempre o da tela aberta, inclusive no voltar', async ({ page }) => {
    // O bug do A-45: em /lotes, clicar num indicador montava a fila no
    // workspace e deixava a tela em Lotes, com o menu marcando o outro item.
    // Corrigido em 2026-09-14; isto é a rede que impede a volta dele.
    await itemDoMenu(page, 'Lotes').click()
    await expect(page).toHaveURL(/\/lotes$/)
    await expect(itemDoMenu(page, 'Lotes')).toHaveAttribute('aria-current', 'page')

    // O indicador abre no workspace, que mora na raiz.
    await itemDoMenu(page, 'Quarentena').click()
    await expect(page).toHaveURL(/\/$/)
    await expect(itemDoMenu(page, 'Quarentena')).toHaveAttribute('aria-current', 'page')
    // E o item da tela anterior larga a marca — era isto que ficava aceso.
    await expect(itemDoMenu(page, 'Lotes')).not.toHaveAttribute('aria-current', 'page')

    // O "voltar" do navegador é o caminho que o `popstate` sintético do
    // Roteador atravessa (ADR-0033): a marca tem de voltar junto com a tela.
    await page.goBack()
    await expect(page).toHaveURL(/\/lotes$/)
    await expect(tituloDaTela(page)).toHaveText('Lotes')
    await expect(itemDoMenu(page, 'Lotes')).toHaveAttribute('aria-current', 'page')
    await expect(itemDoMenu(page, 'Quarentena')).not.toHaveAttribute('aria-current', 'page')
  })
})
