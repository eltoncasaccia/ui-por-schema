import { Etiqueta } from '../ui/Etiqueta'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'

type VM = ViewModel<'produto_ficha'>

/** A classe regulatória muda o que a lei exige do produto, não só a aparência. */
const CLASSE: Record<VM['classe'], string> = {
  comum: 'Comum',
  controlado: 'Controlado',
  termolabil: 'Termolábil',
  antimicrobiano: 'Antimicrobiano',
}

function Campo({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="campo-rotulo">{rotulo}</div>
      <div className="campo-valor">{children}</div>
    </div>
  )
}

/** Centavos → "R$ 12,50". Só é chamado quando o valor existe. */
function reais(centavos: number): string {
  return (centavos / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

/**
 * A ficha do produto. O custo unitário só aparece quando o modelo compôs
 * `variante: 'com_custo'` E o usuário tem `custo.ler` — nesses casos a chave
 * chega no viewmodel; nos demais ela está AUSENTE (CA-05), e o `!= null` abaixo
 * cobre os dois: sem a chave e com `null`.
 *
 * Produto inativo ganha etiqueta, e o saldo continua visível — RN-P05: desativar
 * impede entrada nova, não esconde o que ainda está na prateleira.
 */
export const view: View<'produto_ficha'> = ({ vm }) => (
  <div className="cartao">
    <div className="cartao-cabeca">
      <span className="titulo-painel">{vm.nome}</span>
      <span className="mono fraco" style={{ fontSize: 11 }}>{vm.ean}</span>
    </div>
    <div className="cartao-corpo">
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', margin: '2px 0 4px' }}>
        <Etiqueta tom="neutro">{CLASSE[vm.classe]}</Etiqueta>
        <Etiqueta tom="neutro">Curva {vm.curva_abc}</Etiqueta>
        {!vm.ativo && <Etiqueta tom="laranja">Inativo</Etiqueta>}
      </div>

      <div className="linha-cartao-campos" style={{ marginTop: 12 }}>
        <Campo rotulo="Fabricante">{vm.fabricante}</Campo>
        <Campo rotulo="Princípio ativo">{vm.principio_ativo}</Campo>
        <Campo rotulo="Saldo nas suas unidades">{vm.saldo_total.toLocaleString('pt-BR')}</Campo>
        {vm.custo_unitario_centavos != null && (
          <Campo rotulo="Custo unitário">
            <span className="mono">{reais(vm.custo_unitario_centavos)}</span>
          </Campo>
        )}
        <Campo rotulo="Identificador">
          <span className="mono fraco">{vm.produto_id}</span>
        </Campo>
      </div>
    </div>
  </div>
)
