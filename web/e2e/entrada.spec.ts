import { expect, test } from '@playwright/test'
import { PERSONAS, abrirNavegacao, entrar, type Persona } from './apoio'

/**
 * AC-2 e AC-5 da T-053: quem entra, e o que vê quem não entrou.
 *
 * O `vitest` já monta o `Login` com jsdom. O que só o navegador prova é o
 * cookie de sessão atravessando o proxy do Vite — por isso o AC-5 é o que
 * importa aqui, e ele é negativo.
 */
test.describe('entrada', () => {
  for (const quem of Object.keys(PERSONAS) as Persona[]) {
    const { nome, papel } = PERSONAS[quem]

    test(`AC-2 · ${nome} entra e se reconhece no rodapé`, async ({ page }) => {
      await entrar(page, quem)
      await abrirNavegacao(page)

      const rodape = page.locator('.rodape-ator')
      await expect(rodape).toContainText(nome)
      await expect(rodape).toContainText(papel)
    })
  }

  test('AC-5 · sem sessão, /lotes não mostra lote nenhum', async ({ page }) => {
    await page.goto('/lotes')

    // A tela de entrada, e não a de lotes.
    await expect(page.getByRole('heading', { name: 'Estoque Bertoni' })).toBeVisible()
    await expect(page.getByRole('button', { name: new RegExp(PERSONAS.marco.nome) })).toBeVisible()

    // E nenhuma linha de estoque: sem tabela, sem o título da tela de lotes.
    await expect(page.getByRole('table')).toHaveCount(0)
    await expect(page.locator('h1.workspace-titulo')).toHaveCount(0)
  })

  test('AC-5 · a API recusa o dado sem sessão, em duas camadas', async ({ request }) => {
    // A prova do servidor, ao lado da prova da tela. São DUAS proteções
    // independentes, e o teste separa uma da outra de propósito.

    // 1. Escrita: o CSRF é middleware e vale para TODO POST (T-040). Sem
    //    sessão não há token de duplo envio, então a recusa é dele — e a
    //    requisição nem chega à autenticação. Ordem que vale a pena fixar:
    //    se um dia isto virar 401, o CSRF deixou de ser incondicional.
    const escrita = await request.post('/api/componentes/lote_lista/dados', {
      data: { params: {} },
      headers: { Origin: 'http://localhost:5174' },
    })
    expect(escrita.status()).toBe(403)
    expect(await escrita.text()).toContain('nao_autorizado')

    // 2. Leitura: sem POST não há CSRF no caminho, e quem recusa é a sessão.
    const leitura = await request.get('/api/auth/eu')
    expect(leitura.status()).toBe(401)

    // Nem uma linha de estoque em nenhuma das duas respostas.
    expect(await escrita.text()).not.toContain('linhas')
    expect(await leitura.text()).not.toContain('linhas')
  })
})
