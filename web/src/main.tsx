import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { cache } from './estado/cache'
import './estilo.css'

// Invalidação de pedido superado e coalescing vêm daqui, prontos. A v1 escreveu
// os dois à mão e concluiu que não valeu (ADR-0008).
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={cache}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
