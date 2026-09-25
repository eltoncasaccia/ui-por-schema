import { randomUUID } from 'node:crypto'
import { expect, type Page } from '@playwright/test'

/**
 * As 7 personas do seed (`api/src/estoque/data/seed.py`), com a senha `demo`
 * que a tela de demonstração usa. O papel é o que o rodapé da navegação
 * mostra, cru, como vem de `/api/auth/eu`.
 */
export const PERSONAS = {
  marco: { nome: 'Marco Bertoni', papel: 'diretor' },
  helena: { nome: 'Helena Prado', papel: 'rt' },
  ivo: { nome: 'Ivo Nakamura', papel: 'gerente' },
  odair: { nome: 'Odair Santos', papel: 'gerente' },
  cleide: { nome: 'Cleide Ramos', papel: 'conferente' },
  rafael: { nome: 'Rafael Lima', papel: 'comprador' },
  sandra: { nome: 'Sandra Alves', papel: 'auditoria' },
} as const

export type Persona = keyof typeof PERSONAS

/** Entra pela tela de demonstração. A espera é pelo estado da página — a barra
 * de ícones só existe depois de a sessão valer (ADR-0033 §9). */
export async function entrar(page: Page, quem: Persona): Promise<void> {
  await page.goto('/')
  await page.getByRole('button', { name: new RegExp(PERSONAS[quem].nome) }).click()
  await expect(page.getByRole('button', { name: 'Navegação' })).toBeVisible()
}

/** Garante a lateral de navegação aberta, sem depender do estado inicial dela. */
export async function abrirNavegacao(page: Page): Promise<void> {
  const botao = page.getByRole('button', { name: 'Navegação' })
  if ((await botao.getAttribute('aria-pressed')) !== 'true') await botao.click()
  await expect(page.locator('aside.lateral')).toBeVisible()
}

/** Um item do menu, pelo rótulo — `getByRole` em vez de classe CSS. */
export function itemDoMenu(page: Page, rotulo: string) {
  return page.locator('aside.lateral').getByRole('button', { name: new RegExp(rotulo) })
}

/** O título da tela aberta (`CabecalhoTela`). */
export function tituloDaTela(page: Page) {
  return page.locator('h1.workspace-titulo')
}

/**
 * Lê um componente pela API, com a sessão do navegador e o par de CSRF que o
 * cliente monta (`cookie csrf` + `X-CSRF-Token`, ADR-0019). Serve para o teste
 * obter um dado do seed sem depender de a tabela expor o id na tela.
 */
export async function lerComponente<T>(
  page: Page,
  componente: string,
  params: Record<string, unknown> = {},
): Promise<T> {
  const { dados } = await lerComponenteComEtag<T>(page, componente, params)
  return dados
}

/**
 * Igual a `lerComponente`, mas devolve também o `meta.etag` da leitura
 * (rev. 2.6, T-050) — o que um `If-Match` de escrita compara. T-057 AC-4
 * precisa do etag de ANTES de escrever, para forjar a segunda submissão com
 * o valor velho.
 */
export async function lerComponenteComEtag<T>(
  page: Page,
  componente: string,
  params: Record<string, unknown> = {},
): Promise<{ dados: T; etag: string | undefined }> {
  const csrf = (await page.context().cookies()).find((c) => c.name === 'csrf')?.value ?? ''
  const r = await page.request.post(`/api/componentes/${componente}/dados`, {
    data: { params },
    headers: { 'X-CSRF-Token': csrf, Origin: 'http://localhost:5174' },
  })
  expect(r.ok(), `leitura de ${componente}: ${r.status()} ${await r.text()}`).toBeTruthy()
  const corpo = (await r.json()) as { dados: T; meta: { etag: string | null } }
  return { dados: corpo.dados, etag: corpo.meta.etag ?? undefined }
}

/**
 * Dispara um comando de escrita direto na API, com o CSRF da sessão do
 * navegador — o mesmo par que o cliente monta. Serve para forjar uma
 * tentativa (AC-3, negativo) e para a segunda submissão com etag velho
 * (AC-4), nenhuma das duas alcançável por um clique real na tela.
 */
export async function dispararComandoForcado(
  page: Page,
  endpoint: string,
  corpo: Record<string, unknown>,
  opcoes: { etag?: string; chaveIdempotencia?: string } = {},
) {
  const csrf = (await page.context().cookies()).find((c) => c.name === 'csrf')?.value ?? ''
  return page.request.post(endpoint, {
    data: corpo,
    headers: {
      'X-CSRF-Token': csrf,
      Origin: 'http://localhost:5174',
      'Idempotency-Key': opcoes.chaveIdempotencia ?? randomUUID(),
      ...(opcoes.etag ? { 'If-Match': opcoes.etag } : {}),
    },
  })
}

/**
 * Persiste um schema e devolve o `view_id` público (ADR-0021) — o mesmo
 * `POST /api/views` que `Compartilhar.tsx` chama. T-057 AC-5 usa isto para
 * montar, como Helena, uma composição com um bloco que Cleide não alcança.
 */
export async function criarView(page: Page, titulo: string, schema: unknown): Promise<string> {
  const csrf = (await page.context().cookies()).find((c) => c.name === 'csrf')?.value ?? ''
  const r = await page.request.post('/api/views', {
    data: { titulo, schema },
    headers: { 'X-CSRF-Token': csrf, Origin: 'http://localhost:5174' },
  })
  expect(r.ok(), `criar view: ${r.status()} ${await r.text()}`).toBeTruthy()
  return ((await r.json()) as { dados: { view_id: string } }).dados.view_id
}
