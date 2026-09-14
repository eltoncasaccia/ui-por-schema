import { Etiqueta } from '../ui/Etiqueta'
import { Tabela, type Coluna } from '../ui/Tabela'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'

type VM = ViewModel<'relatorio_movimentacao'>
type Linha = VM['linhas'][number]

function formatar(n: number, medida: VM['unidade_medida']): string {
  if (medida === 'centavos') {
    return (n / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
  }
  return n.toLocaleString('pt-BR')
}

function colunas(vm: VM): Coluna<Linha>[] {
  return [
    { chave: 'rotulo', rotulo: 'Grupo', render: (l) => l.rotulo },
    {
      chave: 'numero',
      rotulo: vm.metrica_rotulo,
      num: true,
      render: (l) => <span className="mono">{formatar(l.numero, vm.unidade_medida)}</span>,
    },
    {
      chave: 'movimentos',
      rotulo: 'Parcela',
      num: true,
      render: (l) => (
        <span className="mono fraco">
          {vm.total ? Math.round((l.numero / vm.total) * 100) : 0}%
        </span>
      ),
    },
  ]
}

/**
 * Relatório agregado (ADR-0029): o eixo e a métrica mudam, a tela não.
 *
 * **O recorte fica sempre à vista**, e a amostra ganha etiqueta própria: um
 * total sobre leitura cortada tem cara de completo, e é exatamente o número
 * errado que parece certo (AC-9).
 */
export const view: View<'relatorio_movimentacao'> = ({ vm }) => (
  <div className="cartao">
    <div className="cartao-cabeca">
      <span className="titulo-painel">
        {vm.metrica_rotulo} {vm.eixo}: {formatar(vm.total, vm.unidade_medida)}
      </span>
      <span className="mono fraco" style={{ fontSize: 11 }}>
        {vm.escopo} · {vm.recorte}
      </span>
    </div>

    <div className="cartao-corpo">
      {vm.truncado && (
        <p style={{ margin: '0 0 12px', fontSize: 13 }}>
          <Etiqueta tom="ambar">
            Amostra: a leitura parou nos movimentos mais recentes — o total não está completo
          </Etiqueta>
        </p>
      )}

      {vm.grupos === 0 ? (
        <p className="fraco" style={{ fontSize: 13, margin: 0 }}>
          Nenhum movimento neste recorte.
        </p>
      ) : (
        <Tabela
          colunas={colunas(vm)}
          linhas={vm.linhas}
          chave={(l) => l.chave}
          titulo={(l) => <span>{l.rotulo}</span>}
          etiqueta={(l) => ({ texto: formatar(l.numero, vm.unidade_medida), tom: 'neutro' })}
        />
      )}

      {vm.tem_mais && (
        <p className="fraco" style={{ fontSize: 12, margin: '8px 0 0' }}>
          Mostrando {vm.linhas.length} de {vm.grupos} grupos.
        </p>
      )}
    </div>
  </div>
)
