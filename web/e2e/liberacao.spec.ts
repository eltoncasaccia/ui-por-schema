import { expect, test } from '@playwright/test'
import { dispararComandoForcado, entrar, lerComponente, lerComponenteComEtag } from './apoio'

/**
 * AC-2, AC-3 e AC-4 da T-057 — a escrita da quarentena exercida por um clique
 * real, e os dois negativos que a T-053 nunca tocou (achado A-48): o caminho
 * inteiro `CSRF → cookie → etag → If-Match → comando` só tinha prova de
 * `curl`, `pytest` e `vitest` com mock, nenhuma delas o navegador.
 *
 * Os três testes rodam em SEQUÊNCIA neste arquivo (Playwright não paraleliza
 * dentro do mesmo arquivo) e cada um lê a fila de novo antes de agir — o lote
 * que o AC-2 libera sai da fila, e o AC-3/AC-4 pegam o que sobrou. Nenhum dos
 * três depende de QUAL lote, só de existir um em quarentena (`estoque_teste`
 * tem 47, achado A-44).
 */
interface FilaQuarentena {
  total: number
  linhas: { lote_id: string; numero: string; produto: string }[]
}

interface LinhaTrilha {
  ator: string | null
  acao: string
  entidade: string | null
  entidade_id: string | null
}

test.describe('liberação de quarentena', () => {
  test('AC-2 · Helena libera um lote pela interface, em clique real', async ({ page }) => {
    await entrar(page, 'helena')
    const fila = await lerComponente<FilaQuarentena>(page, 'quarentena_fila')
    expect(fila.linhas.length).toBeGreaterThan(0)
    // O ÚLTIMO da fila, não o primeiro: `catalogo.spec.ts` (AC-4) e
    // `compartilhamento.spec.ts` (AC-5) leem `linhas[0]` sem escrever, e
    // rodam em arquivos diferentes — Playwright paraleliza entre arquivos.
    // Escrever de verdade no MESMO lote que outro arquivo está lendo
    // colidiria com o pressuposto deles de que ninguém mais mexeu na fila.
    const alvo = fila.linhas[fila.linhas.length - 1]!

    // Identificador digitado ou colado, não buscado — o mesmo padrão que
    // `lote_detalhe` e `TelaSaida` já usam (comentário de `TelaSaida.tsx`).
    await page.goto(`/quarentena/${alvo.lote_id}`)
    await expect(page.locator('main.workspace').getByText(`Liberação · lote ${alvo.numero}`)).toBeVisible()

    // Marca toda a conferência — os itens obrigatórios variam com a classe do
    // produto (RN-R03), e marcar os opcionais também não atrapalha a decisão.
    for (const caixa of await page.locator('main.workspace input[type="checkbox"]').all()) {
      await caixa.check()
    }
    await page
      .getByLabel('Justificativa')
      .fill('Conferência completa: embalagem íntegra, validade e nota fiscal ok.')

    // `confirm: true` arma a tentativa no primeiro clique (T-049 AC-2) — só o
    // segundo grava.
    await page.locator('main.workspace').getByRole('button', { name: 'Liberar', exact: true }).click()
    await expect(page.getByText('Confirmar esta ação?')).toBeVisible()
    await page.getByRole('button', { name: 'Confirmar' }).click()

    // A fila perde o lote — a mesma leitura de antes, agora sem ele.
    await expect
      .poll(async () => {
        const depois = await lerComponente<FilaQuarentena>(page, 'quarentena_fila')
        return depois.linhas.map((l) => l.lote_id)
      })
      .not.toContain(alvo.lote_id)

    // A trilha registra a operação com a identidade dela. Helena tem
    // `auditoria.ler` (RT, `PERMISSOES_POR_PAPEL`) — a prova é ela mesma lendo
    // a própria trilha, sem precisar de uma segunda persona.
    const trilha = await lerComponente<{ linhas: LinhaTrilha[] }>(page, 'auditoria_trilha', {
      entidade: 'lote',
      ator_id: 'u-helena',
      periodo: 'tudo',
    })
    const registro = trilha.linhas.find(
      (l) => l.entidade_id === alvo.lote_id && l.acao === 'lote_liberar_quarentena',
    )
    expect(registro, `nenhum registro de lote_liberar_quarentena para ${alvo.lote_id} na trilha de Helena`).toBeTruthy()
    expect(registro?.ator).toBe('u-helena')
  })

  test('AC-3 · (negativo) Cleide forja o comando, com CSRF válido da própria sessão, e é recusada', async ({
    page,
  }) => {
    await entrar(page, 'cleide')
    const antes = await lerComponente<FilaQuarentena>(page, 'quarentena_fila')
    expect(antes.linhas.length).toBeGreaterThan(0)
    const alvo = antes.linhas[0]!

    // Cleide não tem `lote.liberar` (conferente, `PERMISSOES_POR_PAPEL`). O
    // CSRF é o par legítimo da PRÓPRIA sessão dela — a prova não é a ausência
    // do botão (ela nem vê a tela), é a autorização dentro do comando
    // (ADR-0004, terceiro momento).
    const r = await dispararComandoForcado(page, '/api/comandos/lote_liberar_quarentena', {
      lote_id: alvo.lote_id,
      decisao: 'liberar',
      justificativa: 'tentativa forjada por quem não pode decidir',
      integridade_conferida: true,
      validade_conferida: true,
      nota_fiscal_conferida: true,
      temperatura_conferida: true,
    })
    expect(r.status()).toBe(403)
    expect(await r.text()).toContain('nao_autorizado')

    // O lote continua em quarentena — nada foi aplicado.
    const depois = await lerComponente<FilaQuarentena>(page, 'quarentena_fila')
    expect(depois.linhas.map((l) => l.lote_id)).toContain(alvo.lote_id)
  })

  test('AC-4 · (negativo) segunda submissão com o etag velho devolve conflito, e nada é aplicado', async ({
    page,
  }) => {
    await entrar(page, 'helena')
    const fila = await lerComponente<FilaQuarentena>(page, 'quarentena_fila')
    expect(fila.linhas.length).toBeGreaterThan(0)
    // O último, pelo mesmo motivo do AC-2: este teste ESCREVE de verdade.
    const alvo = fila.linhas[fila.linhas.length - 1]!

    // O etag de ANTES de escrever — o que uma aba desatualizada ainda teria em
    // mãos (T-050: `meta.etag` de `POST /api/componentes/{id}/dados`).
    const { etag: etagVelho } = await lerComponenteComEtag(page, 'quarentena_liberar', {
      lote_id: alvo.lote_id,
    })
    if (!etagVelho) throw new Error(`sem etag para quarentena_liberar/${alvo.lote_id}`)

    const corpo = {
      lote_id: alvo.lote_id,
      decisao: 'liberar' as const,
      justificativa: 'primeira submissão, com o etag correto',
      integridade_conferida: true,
      validade_conferida: true,
      nota_fiscal_conferida: true,
      temperatura_conferida: true,
    }

    // A primeira submissão, com o etag certo, é aceita.
    const primeira = await dispararComandoForcado(page, '/api/comandos/lote_liberar_quarentena', corpo, {
      etag: etagVelho,
    })
    expect(primeira.ok(), `primeira submissão: ${primeira.status()} ${await primeira.text()}`).toBeTruthy()

    // A segunda, com o MESMO etag — agora velho, porque o primeiro comando já
    // mudou o registro — é um conflito. Chave de idempotência NOVA: com a
    // mesma chave da primeira, o pipeline faria replay em vez de tentar
    // escrever de novo, e não é isso que este teste mede.
    const segunda = await dispararComandoForcado(
      page,
      '/api/comandos/lote_liberar_quarentena',
      { ...corpo, justificativa: 'segunda submissão, com o etag velho' },
      { etag: etagVelho },
    )
    expect(segunda.status()).toBe(409)
    // A mensagem do IF-MATCH especificamente, não só o código "conflito": a
    // máquina de estados (`_transicionar`) TAMBÉM devolve 409 quando o
    // segundo "liberar" bate num lote que já saiu de quarentena — duas
    // proteções independentes, o mesmo código. Checar só o código deixaria
    // este teste verde mesmo com o `If-Match` desligado (a sabotagem do AC-7
    // encontrou isto: sem a checagem de etag, a máquina de estados barra a
    // MESMA tentativa por outro motivo, e o teste não notaria a diferença).
    expect(await segunda.text()).toContain('O registro mudou desde a leitura')

    // Nada da segunda foi aplicado: a trilha tem UM registro de decisão para
    // este lote, não dois — reler confirma que o conflito não gravou por
    // baixo.
    const trilha = await lerComponente<{ linhas: LinhaTrilha[] }>(page, 'auditoria_trilha', {
      entidade: 'lote',
      ator_id: 'u-helena',
      periodo: 'tudo',
    })
    const registros = trilha.linhas.filter(
      (l) => l.entidade_id === alvo.lote_id && l.acao === 'lote_liberar_quarentena',
    )
    expect(registros.length).toBe(1)
  })
})
