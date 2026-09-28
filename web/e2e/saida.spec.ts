import { expect, test, type Page } from '@playwright/test'
import { entrar, lerComponente } from './apoio'

/**
 * Saída com FEFO, pelo navegador — o fluxo de escrita que faltava.
 *
 * A T-057 provou a quarentena por clique real e parou ali (achado A-48). A
 * saída é o outro caminho de escrita que um operador percorre todo dia, e o
 * único onde a regra decide **qual lote** sai: `RN-L03` manda propor o de
 * validade mais próxima e exige justificativa de quem separar outro.
 *
 * Estes testes encontraram o [A-52](../../docs/tasks/ACHADOS.md): o botão
 * ficava habilitado com cliente e nota vazios, o servidor recusava com
 * "Entrada invalida." e o operador só descobria depois de confirmar.
 *
 * O produto é `p-amoxicilina`, id determinístico do seed. Nenhum teste depende
 * de QUAL lote é proposto.
 *
 * **Ordem importa.** O Playwright não paraleliza dentro de um arquivo: os dois
 * negativos não escrevem e vêm primeiro; a escrita de verdade vem por último,
 * para não mudar o saldo debaixo deles.
 */
interface Candidato {
  lote_id: string
  numero: string
  disponivel: boolean
}
interface VMSaida {
  produto: string
  proposta?: Candidato | null
  alternativas?: Candidato[]
  sem_estoque?: boolean
  exige_autorizacao: boolean
}
interface VMLote {
  saldo: number
  numero: string
}

const PRODUTO = 'p-amoxicilina'
/** "Venda" — o único motivo que exige destinatário, e o caso real do dia a dia. */
const VENDA = 'Venda'
const ENVIAR = /Registrar saída|Enviar para autorização/

/** O portão de `/saida`: sem produto não existe bloco, e nada foi carregado. */
async function abrirSeparacao(page: Page): Promise<void> {
  await page.goto('/saida')
  await page.getByLabel('Id do produto').fill(PRODUTO)
  await page.getByRole('button', { name: 'Continuar' }).click()
  await expect(page.locator('#quantidade-saida')).toBeVisible()
}

test.describe('saída com FEFO', () => {
  test('(negativo) trocar o lote proposto trava o envio até a justificativa ter 10 caracteres', async ({
    page,
  }) => {
    await entrar(page, 'ivo')
    const vm = await lerComponente<VMSaida>(page, 'movimento_saida', { produto_id: PRODUTO })
    expect((vm.alternativas ?? []).some((c) => c.disponivel)).toBe(true)

    await abrirSeparacao(page)
    const enviar = page.getByRole('button', { name: ENVIAR })
    const lotes = page.locator('input[name="lote-saida"]:not([disabled])')

    // Com a PROPOSTA marcada e um motivo sem destinatário, o envio libera.
    await lotes.first().check()
    await page.locator('#quantidade-saida').fill('1')
    await page.locator('#motivo-saida').selectOption({ label: 'Avaria' })
    await expect(enviar).toBeEnabled()

    // Trocar para a alternativa trava — e a tela diz por quê, citando a regra.
    await lotes.nth(1).check()
    await expect(enviar).toBeDisabled()
    await expect(page.getByText(/justificativa registrada \(RN-L03\)/)).toBeVisible()

    // Uma palavra não é justificativa: o mínimo de 10 caracteres é o que
    // separa um registro de auditoria de um campo preenchido por reflexo.
    await page.locator('#justificativa-fefo').fill('urgente')
    await expect(enviar).toBeDisabled()

    await page.locator('#justificativa-fefo').fill('cliente pediu validade mais longa')
    await expect(enviar).toBeEnabled()
  })

  test('(negativo) A-52 · motivo que exige destinatário trava o envio sem cliente e nota', async ({
    page,
  }) => {
    await entrar(page, 'ivo')
    await abrirSeparacao(page)
    const enviar = page.getByRole('button', { name: ENVIAR })

    await page.locator('input[name="lote-saida"]:not([disabled])').first().check()
    await page.locator('#quantidade-saida').fill('1')
    await page.locator('#motivo-saida').selectOption({ label: VENDA })

    // Antes do A-52 o botão ficava habilitado aqui, o comando saía com
    // `cliente_id: ""`, e o 422 chegava DEPOIS da confirmação.
    await expect(page.locator('#cliente-saida')).toBeVisible()
    await expect(enviar).toBeDisabled()
    await expect(page.getByText('Saída com destinatário exige cliente e nota fiscal.')).toBeVisible()

    // Só um dos dois também não basta.
    await page.locator('#cliente-saida').fill('c-farmacia-central')
    await expect(enviar).toBeDisabled()

    await page.locator('#nota-saida').fill('NF-99001')
    await expect(enviar).toBeEnabled()
  })

  test('Ivo separa pelo lote proposto, em clique real, e o saldo cai', async ({ page }) => {
    await entrar(page, 'ivo')
    const antes = await lerComponente<VMSaida>(page, 'movimento_saida', { produto_id: PRODUTO })
    expect(antes.sem_estoque ?? false).toBe(false)
    const proposto = antes.proposta!
    const saldoAntes = (
      await lerComponente<VMLote>(page, 'lote_detalhe', { lote_id: proposto.lote_id })
    ).saldo
    expect(saldoAntes).toBeGreaterThan(0)

    await abrirSeparacao(page)
    await page.locator('input[name="lote-saida"]:not([disabled])').first().check()
    await page.locator('#quantidade-saida').fill('1')
    await page.locator('#motivo-saida').selectOption({ label: VENDA })
    await page.locator('#cliente-saida').fill('c-farmacia-central')
    await page.locator('#nota-saida').fill('NF-99001')

    // `confirm: true` no CommandDef: o primeiro clique arma, só o segundo grava.
    await page.getByRole('button', { name: ENVIAR }).click()
    await expect(page.getByText('Confirmar esta ação?')).toBeVisible()
    await page.getByRole('button', { name: 'Confirmar' }).click()

    // Nenhum erro na tela — o cartão de tentativa some quando o comando passa.
    await expect(page.getByText('Entrada invalida.')).toHaveCount(0)

    // A prova é o SALDO, lido de novo pela API. Asserção em texto de sucesso
    // passa com o comando falhando em silêncio, e foi assim que a primeira
    // versão deste teste escondeu o A-52.
    await expect
      .poll(
        async () =>
          (await lerComponente<VMLote>(page, 'lote_detalhe', { lote_id: proposto.lote_id })).saldo,
        { message: `saldo do lote ${proposto.numero} deveria cair de ${saldoAntes} para ${saldoAntes - 1}` },
      )
      .toBe(saldoAntes - 1)
  })
})
