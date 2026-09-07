import type { View } from './tipos'

export interface Linha {
  lote_id: string
  produto: string
  numero: string
  unidade: string
  validade: string
  dias_restantes: number
  saldo: number
  situacao: 'ok' | 'alerta_90' | 'bloqueio_30' | 'vencido'
}
export interface VM { janela_dias: number; total: number; linhas: Linha[] }

const ROTULO: Record<Linha['situacao'], string> = {
  ok: 'Ok',
  alerta_90: 'Alerta 90d',
  bloqueio_30: 'Bloqueio 30d',
  vencido: 'Vencido',
}
const CLASSE: Record<Linha['situacao'], string> = {
  ok: 'ok', alerta_90: 'alerta', bloqueio_30: 'alerta', vencido: 'perigo',
}

export const view: View<VM> = ({ vm }) => (
  <div>
    <p className="suave" style={{ margin: '0 0 .75rem' }}>
      {vm.total} lote{vm.total === 1 ? '' : 's'} vencendo em até {vm.janela_dias} dias
    </p>
    {vm.total === 0 ? (
      <p className="suave">Nada vencendo nesta janela.</p>
    ) : (
      <div className="rolagem">
        <table>
          <thead>
            <tr>
              <th>Produto</th><th>Lote</th><th>Unidade</th>
              <th>Validade</th><th>Dias</th><th>Saldo</th><th>Situação</th>
            </tr>
          </thead>
          <tbody>
            {vm.linhas.map((l) => (
              <tr key={l.lote_id}>
                <td>{l.produto}</td>
                <td className="mono">{l.numero}</td>
                <td className="suave">{l.unidade}</td>
                <td className="mono">{l.validade}</td>
                <td className="mono">{l.dias_restantes}</td>
                <td className="mono">{l.saldo}</td>
                <td><span className={`pilula ${CLASSE[l.situacao]}`}>{ROTULO[l.situacao]}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </div>
)
