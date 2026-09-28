/**
 * Filtro interativo, ao redor do bloco (T-055, achado A-46).
 *
 * Mesmo lugar do botão de exportar (`BotaoExportar.tsx`, T-054), pelo mesmo
 * motivo: preserva CONTRATOS §6 (`View<Id>` só recebe `vm`) sem mudar nada
 * nela, e funciona nas duas superfícies de graça — rota tradicional e
 * composição do assistente passam pelo MESMO `render/motor.tsx` (ADR-0017).
 *
 * Só existe campo aqui se `FILTROS[tipo]` tiver ele, e `FILTROS` só tem
 * campo com `enum` no `Params` do lado servidor (`campos_filtraveis`,
 * `exportar.py`). Identificador nunca tem enum — nunca aparece aqui, por
 * construção, não por lista de exclusão do lado cliente.
 */
import type { ComponentId } from '../generated/componentes'
import { FILTROS } from '../generated/componentes'
import { rotuloCampo, rotuloValor } from './rotulosFiltro'

export function BarraFiltro({
  tipo, valores, aoMudar,
}: {
  // `string`, como `BotaoExportar` — `bloco.tipo` é string na borda (o id
  // vem da API, o cliente não garante que é um `ComponentId` conhecido).
  tipo: string
  valores: Record<string, unknown>
  aoMudar: (campo: string, valor: string) => void
}) {
  const campos = FILTROS[tipo as ComponentId]
  if (!campos) return null
  const entradas = Object.entries(campos)
  if (entradas.length === 0) return null

  return (
    <div className="filtro" role="group" aria-label="Filtrar">
      {entradas.map(([campo, opcoes]) => (
        <label key={campo} className="filtro-campo">
          <span className="filtro-rotulo">{rotuloCampo(campo)}</span>
          <select
            className="filtro-select"
            value={typeof valores[campo] === 'string' ? valores[campo] : ''}
            onChange={(e) => aoMudar(campo, e.target.value)}
          >
            {opcoes.map((v) => (
              <option key={v} value={v}>
                {rotuloValor(tipo, campo, v)}
              </option>
            ))}
          </select>
        </label>
      ))}
    </div>
  )
}
