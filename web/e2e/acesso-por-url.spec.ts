import { expect, test } from '@playwright/test'
import { entrar } from './apoio'

/**
 * AC-9 da T-057 — a taxonomia que a corrida da skill `e2e-nav-test` de
 * 2026-09-25 descobriu (achado A-48): as 10 falhas dela eram todas "acesso
 * negado por URL" tratadas como um caso só, e são TRÊS. Ausência de menu não
 * implica negativa na URL — o menu é conveniência (ADR-0003 §"Riscos
 * aceitos"); quem decide é a autorização em cada `load` (ADR-0004).
 *
 * Marco (diretor) não tem `recebimento.criar`, `controlado.autorizar` nem
 * `movimento.criar` — só `lote.ler` (`PERMISSOES_POR_PAPEL`, verificado no
 * `/api/catalogo` das 7 personas em 2026-09-25). É por isso que ele serve os
 * três casos.
 */
test.describe('acesso negado por URL', () => {
  test('negado no carregamento · /recebimento/novo', async ({ page }) => {
    await entrar(page, 'marco')
    await page.goto('/recebimento/novo')

    await expect(page.locator('main.workspace').getByText('Sem acesso a este componente.')).toBeVisible()
    // Nenhum dado do componente aparece — nem o campo que o formulário abriria.
    await expect(page.locator('main.workspace').getByLabel('Código de barras do produto')).toHaveCount(0)
  })

  test('negado no carregamento · /controlados', async ({ page }) => {
    await entrar(page, 'marco')
    await page.goto('/controlados')

    await expect(page.locator('main.workspace').getByText('Sem acesso a este componente.')).toBeVisible()
    // O título PRÓPRIO da view (distinto do título da rota, que é só
    // "Controlados" e continua aparecendo no cabeçalho de qualquer jeito).
    await expect(page.locator('main.workspace').getByText('Controlados aguardando autorização')).toHaveCount(0)
  })

  test('lido sem poder agir · /quarentena', async ({ page }) => {
    await entrar(page, 'marco')
    await page.goto('/quarentena')

    // A fila CARREGA — `quarentena_fila` é `lote.ler`, que Marco tem. Não há
    // "sem acesso" nenhum aqui: o que se afirma é a ausência de caminho para
    // liberar.
    await expect(page.locator('main.workspace').getByText('Fila de quarentena')).toBeVisible()
    await expect(page.locator('main.workspace').getByText('Sem acesso a este componente.')).toHaveCount(0)
    // Nenhum botão de liberação na tela, nem desabilitado — a tabela é
    // só-leitura de propósito (`ui/Tabela.tsx` não conhece navegação nenhuma).
    await expect(page.locator('main.workspace').getByRole('button', { name: /liberar/i })).toHaveCount(0)
  })

  test('portão de formulário · /saida', async ({ page }) => {
    await entrar(page, 'marco')
    await page.goto('/saida')

    // ANTES de qualquer busca: sem produto ainda não há bloco, e portanto
    // nenhum `load` foi tentado — nenhuma recusa existe ainda.
    await expect(page.getByText('Informe o id do produto para começar a separação.')).toBeVisible()
    await expect(page.getByText('Sem acesso a este componente.')).toHaveCount(0)

    // Só ao submeter o `movimento_saida` vira um bloco de verdade, e a recusa
    // chega — Marco não tem `movimento.criar` (negativo: sem a submissão,
    // este caso não prova nada, exatamente o que o AC-9 pede).
    await page.getByLabel('Id do produto').fill('p-losartana')
    await page.getByRole('button', { name: 'Continuar' }).click()

    await expect(page.locator('main.workspace').getByText('Sem acesso a este componente.')).toBeVisible()
  })
})
