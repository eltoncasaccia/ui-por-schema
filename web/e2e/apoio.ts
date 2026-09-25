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
  const csrf = (await page.context().cookies()).find((c) => c.name === 'csrf')?.value ?? ''
  const r = await page.request.post(`/api/componentes/${componente}/dados`, {
    data: { params },
    headers: { 'X-CSRF-Token': csrf, Origin: 'http://localhost:5174' },
  })
  expect(r.ok(), `leitura de ${componente}: ${r.status()} ${await r.text()}`).toBeTruthy()
  return ((await r.json()) as { dados: T }).dados
}
