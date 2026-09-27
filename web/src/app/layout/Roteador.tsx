import type { ReactNode } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import type { Eu } from '../../api'
import { TelaOperacao } from '../telas/TelaOperacao'
import { TelaRecebimento } from '../telas/TelaRecebimento'
import { TelaSaida } from '../telas/TelaSaida'
import { TelaUsuarios } from '../telas/usuarios'
import { ROTAS_OPERACAO } from './rotasOperacao'

/**
 * As 8 rotas de operação, mais o que já existia — `/` e `/v/:viewId` caem no
 * `*` e continuam exatamente como estavam, sob o `Workspace` do assistente em
 * `App.tsx` (não tocado): o próprio `useRotaView` de `rotas.tsx` continua
 * resolvendo esses dois casos, deste roteador para fora.
 *
 * `movimento_saida` é o único componente cujo param obrigatório não vem da
 * URL — ver `TelaSaida.tsx`. As outras sete rotas são todas a mesma forma:
 * path → params da URL → um bloco → `Composicao` (`TelaOperacao.tsx`).
 *
 * `irPara`/`substituirPor` (`rotas.tsx`) continuam navegando por
 * `history.pushState` direto — por isso `anunciar()` lá agora também dispara
 * um `popstate` sintético: é o único jeito de o `history` interno deste
 * `BrowserRouter` ficar sabendo de uma navegação que ele não iniciou.
 */
export function Roteador({ eu, workspace }: { eu: Eu; workspace: ReactNode }) {
  return (
    <BrowserRouter>
      <Routes>
        {ROTAS_OPERACAO.map((rota) => (
          <Route
            key={rota.path}
            path={rota.path}
            element={
              rota.path === '/saida' ? (
                <TelaSaida eu={eu} />
              ) : rota.path === '/recebimento/novo' ? (
                <TelaRecebimento rota={rota} eu={eu} />
              ) : (
                <TelaOperacao rota={rota} eu={eu} />
              )
            }
          />
        ))}
        {/* T-038 — fora do catálogo: não é componente, então não entra em ROTAS_OPERACAO. */}
        <Route path="/usuarios" element={<TelaUsuarios eu={eu} />} />
        <Route path="*" element={<>{workspace}</>} />
      </Routes>
    </BrowserRouter>
  )
}
