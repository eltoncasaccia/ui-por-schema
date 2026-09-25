import { defineConfig, devices } from '@playwright/test'

/**
 * E2E da T-053, nos termos do ADR-0033.
 *
 * Os dois servidores são NOSSOS, em portas próprias (8001/5174), contra o
 * database `estoque_teste`. Reusar o stack do `make up` é exatamente como o
 * A-44 volta: `movimento` e `auditoria` são append-only, e sessão de teste
 * gravada no banco de desenvolvimento não se apaga depois.
 */
const API = 'http://localhost:8001'
const WEB = 'http://localhost:5174'

// Papel restrito (`estoque_app`), nunca o dono: é o mesmo endereço que
// `api/tests/banco.py` publica, e é o que faz a imutabilidade valer aqui
// também (A-27).
const BANCO =
  process.env.DATABASE_URL_E2E ??
  'postgresql+asyncpg://estoque_app:app@localhost:15432/estoque_teste'

export default defineConfig({
  testDir: './e2e',
  // Espera fixa é proibida (ADR-0033 §9); toda asserção espera pelo estado da
  // página. Este teto existe para o teste falhar em vez de pendurar o CI.
  timeout: 30_000,
  expect: { timeout: 10_000 },
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['html'], ['list']] : [['list']],

  use: {
    baseURL: WEB,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  // Só Chromium no ciclo 1. Firefox, WebKit e o layout estreito ficam
  // registrados no ADR-0033 como não verificados.
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],

  webServer: [
    {
      command: 'uv run uvicorn estoque.server.app:app --port 8001',
      cwd: '../api',
      url: `${API}/api/saude`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        DATABASE_URL: BANCO,
        SESSAO_SECRET: 'e2e-nao-usar-fora-do-teste',
        MODO_DEMO: 'true',
        // O CSRF compara `Origin` com isto — se divergir da origem do Vite de
        // e2e, todo POST do teste é recusado antes de chegar ao domínio.
        CORS_ORIGIN: WEB,
        // Nenhuma chave de provedor (AC-9): o e2e não chama modelo, e chamar
        // custaria token a cada execução (ADR-0013).
      },
    },
    {
      command: 'npm run dev -- --port 5174 --strictPort',
      url: WEB,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { VITE_API_URL: API },
    },
  ],
})
