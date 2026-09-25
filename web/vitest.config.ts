import react from '@vitejs/plugin-react'
import { configDefaults, defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/testes/preparo.ts',
    // As specs de `e2e/` são do Playwright (T-053, ADR-0033) e rodam por
    // `make e2e`, fora do `make check`. Sem esta linha o `vitest` as coleta
    // pelo nome, não encontra teste nenhum dentro delas — porque `test()` ali
    // é do outro runner — e reprova três arquivos sem nada estar errado.
    exclude: [...configDefaults.exclude, 'e2e/**'],
  },
})
