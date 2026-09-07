import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      // O cliente fala com a API por caminho relativo. Sem CORS no navegador,
      // e o cookie de sessão é same-origin — que é o que faz SameSite=Lax
      // proteger de verdade (ADR-0019).
      '/api': { target: process.env.VITE_API_URL ?? 'http://localhost:8000', changeOrigin: true },
    },
  },
})
