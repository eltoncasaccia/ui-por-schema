import { expect, test } from '@playwright/test'
import { criarView, entrar, lerComponente } from './apoio'

/**
 * AC-5 da T-057 (achado A-48, achado A-36 da T-016): `/v/:viewId` só tinha
 * prova de servidor — abrir view não devolve dado, e bloco fora do catálogo
 * de quem abre some (`schema/validar.py:validar_schema`). No navegador, com
 * dois atores de verdade, nunca foi testado.
 */
interface FilaQuarentena {
  total: number
  linhas: { lote_id: string; numero: string; produto: string }[]
}

test.describe('view compartilhada', () => {
  test('AC-5 · Helena compõe dois blocos, Cleide abre e perde o que não é dela — e a tela não quebra', async ({
    browser,
  }) => {
    const deHelena = await browser.newContext()
    const helena = await deHelena.newPage()
    await entrar(helena, 'helena')

    // Um bloco que as duas alcançam (`lote_lista`, `lote.ler`), e um que só
    // Helena alcança (`quarentena_liberar`, `lote.liberar` — RT, RN-R02). O
    // id vem da fila de verdade: o teste não inventa um lote do seed.
    const fila = await lerComponente<FilaQuarentena>(helena, 'quarentena_fila')
    expect(fila.linhas.length).toBeGreaterThan(0)
    const alvo = fila.linhas[0]!

    const viewId = await criarView(helena, 'Composição de teste — AC-5', {
      versao: 1,
      blocos: [
        { tipo: 'lote_lista', params: {} },
        { tipo: 'quarentena_liberar', params: { lote_id: alvo.lote_id } },
      ],
    })

    const deCleide = await browser.newContext()
    const cleide = await deCleide.newPage()
    await entrar(cleide, 'cleide')
    await cleide.goto(`/v/${viewId}`)

    // O que ela PODE ver continua renderizando — a tela não quebra por causa
    // do bloco que sumiu. `titulo-painel`, não `table`: com o assistente e a
    // navegação abertos por padrão, `main.workspace` fica estreito o
    // suficiente para `Tabela` virar lista de cartões (`ui/Tabela.tsx`), e o
    // título do cartão é o que continua estável nos dois modos.
    await expect(cleide.locator('main.workspace').getByText('Lotes', { exact: true })).toBeVisible()

    // O que ela NÃO PODE ver — a liberação deste lote específico — não
    // aparece em lugar nenhum: nem o título do formulário, nem o número do
    // lote, nem uma mensagem de "sem acesso" no lugar dele. `validar_schema`
    // remove o bloco fora do catálogo do ator ANTES de a resposta sair do
    // servidor — diferente do `nao_autorizado` que `/quarentena/:loteId`
    // mostraria se ela tentasse o endereço direto (AC-9): aqui o bloco nunca
    // chegou a ser pedido.
    await expect(cleide.locator('main.workspace').getByText(/^Liberação · lote/)).toHaveCount(0)
    await expect(cleide.locator('main.workspace')).not.toContainText(alvo.numero)
    await expect(cleide.locator('main.workspace').getByText('Sem acesso')).toHaveCount(0)

    // E nenhum erro de rota tomou o lugar da composição — a tela abriu.
    await expect(cleide.getByText('Não foi possível abrir este endereço.')).toHaveCount(0)
    await expect(cleide.getByText('Este endereço não está mais disponível.')).toHaveCount(0)

    await deHelena.close()
    await deCleide.close()
  })
})
