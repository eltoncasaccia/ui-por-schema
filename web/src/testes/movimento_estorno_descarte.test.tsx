/**
 * T-029 — as duas telas de correção, e o que elas se recusam a deixar enviar.
 *
 * O que a view garante é o **primeiro** dos três avisos do `ADR-0004`, e o mais
 * fraco: ela desabilita, o servidor recusa, e o banco recusa de novo. Testá-la
 * não prova a regra — prova que o operador é avisado antes de tentar, que é o
 * que separa uma recusa entendida de uma recusa que parece defeito.
 *
 * Os casos aqui são os que a tarefa nomeia do lado do cliente:
 *
 *   AC-6  lote liberado e válido aparece com o impedimento, e não selecionável
 *   AC-7  sem a segunda identificação o botão não envia
 *   RN-M03 o par original/estorno aparece inteiro — nada some do extrato
 */
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ViewModel } from '../generated/componentes'
import { view as Descarte } from '../views/movimento_descarte'
import { view as Estorno } from '../views/movimento_estorno'

type VMEstorno = ViewModel<'movimento_estorno'>
type VMDescarte = ViewModel<'movimento_descarte'>
type Lancamento = NonNullable<VMEstorno['lancamentos']>[number]
type LoteDescartavel = NonNullable<VMDescarte['fila']>[number]

const SAIDA: Lancamento = {
  movimento_id: 'm-06',
  tipo: 'saida',
  quantidade: 60,
  motivo: 'venda',
  autor: 'u-cleide',
  registrado_em: '2026-09-01T10:00:00Z',
  estorna_movimento_id: null,
  pode_estornar: true,
  impedimento: null,
  etag: 'etag-saida',
}
const ENTRADA: Lancamento = {
  ...SAIDA,
  movimento_id: 'm-05',
  tipo: 'entrada',
  motivo: 'recebimento',
  pode_estornar: false,
  impedimento: 'Movimento de entrada não tem estorno neste ciclo.',
}
const ESTORNO_DE_M02: Lancamento = {
  ...SAIDA,
  movimento_id: 'm-12',
  tipo: 'estorno',
  motivo: 'estorno',
  estorna_movimento_id: 'm-02',
  pode_estornar: false,
  impedimento: 'Um estorno não se estorna (RN-M03).',
}

function vmEstorno(over: Partial<VMEstorno> = {}): VMEstorno {
  return {
    produto: 'Amoxicilina 500mg',
    lote: 'AMX2405',
    unidade: 'CD Matriz',
    saldo: 0,
    total: 2,
    lancamentos: [SAIDA, ENTRADA],
    alvo: null,
    motivos: [
      { valor: 'erro_de_separacao', rotulo: 'Erro de separação' },
      { valor: 'estorno', rotulo: 'Cancelamento da operação' },
    ],
    ...over,
  }
}

const VENCIDO: LoteDescartavel = {
  lote_id: 'l-amox-venc',
  produto: 'Amoxicilina 500mg',
  numero: 'AMX2312',
  unidade: 'CD Matriz',
  validade: '2026-08-20',
  dias_restantes: -10,
  saldo: 80,
  status_efetivo: 'vencido',
  pode_descartar: true,
  impedimento: null,
  etag: 'etag-vencido',
}
const LIBERADO: LoteDescartavel = {
  ...VENCIDO,
  lote_id: 'l-amox-mtz',
  numero: 'AMX2401',
  validade: '2027-03-01',
  dias_restantes: 200,
  status_efetivo: 'liberado',
  pode_descartar: false,
  impedimento: 'Está liberado: descarte é para lote vencido ou bloqueado (RN-L06).',
}

function vmDescarte(over: Partial<VMDescarte> = {}): VMDescarte {
  return {
    total: 1,
    escopo: '2 unidades',
    fila: [VENCIDO],
    alvo: null,
    motivos: [
      { valor: 'vencimento', rotulo: 'Vencimento' },
      { valor: 'avaria', rotulo: 'Avaria, recall ou suspeita' },
    ],
    exige_dupla_identificacao: true,
    ...over,
  }
}

function botao(nome: RegExp): HTMLButtonElement {
  return screen.getByRole('button', { name: nome })
}

function radios(): HTMLInputElement[] {
  return screen.getAllByRole<HTMLInputElement>('radio')
}

/** O primeiro selecionável. `noUncheckedIndexedAccess` cobra a checagem, e a
 *  mensagem explícita é melhor do que um `undefined` estourando no `fireEvent`. */
function primeiroRadio(): HTMLInputElement {
  const [primeiro] = radios()
  if (!primeiro) throw new Error('a tela não desenhou nenhuma opção')
  return primeiro
}

describe('movimento_estorno', () => {
  it('o lançamento estornável é selecionável e o que não é fica desabilitado', () => {
    render(<Estorno vm={vmEstorno()} />)
    const opcoes = radios()
    expect(opcoes).toHaveLength(2)
    expect(opcoes.filter((r) => !r.disabled)).toHaveLength(1)
  })

  it('o motivo de não poder estornar fica na tela, junto do lançamento', () => {
    render(<Estorno vm={vmEstorno()} />)
    expect(screen.getByText(/não tem estorno neste ciclo/)).toBeInTheDocument()
  })

  it('RN-M03: o par original e estorno aparece inteiro', () => {
    render(<Estorno vm={vmEstorno({ lancamentos: [SAIDA, ESTORNO_DE_M02], total: 2 })} />)
    expect(screen.getByText('m-02')).toBeInTheDocument()
    expect(screen.getByText(/Um estorno não se estorna/)).toBeInTheDocument()
  })

  it('a tela diz que o estorno cria movimento novo, antes de escolher', () => {
    render(<Estorno vm={vmEstorno()} />)
    expect(screen.getByText(/Nada é apagado nem editado/)).toBeInTheDocument()
  })

  it('sem motivo e sem explicação o botão não envia', () => {
    render(<Estorno vm={vmEstorno()} />)
    expect(botao(/Registrar estorno/)).toBeDisabled()
  })

  it('com lançamento, motivo e explicação suficiente, envia', () => {
    render(<Estorno vm={vmEstorno()} />)
    fireEvent.click(primeiroRadio())
    fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: 'erro_de_separacao' } })
    fireEvent.change(screen.getByLabelText('O que aconteceu'), {
      target: { value: 'separou o lote errado na conferência' },
    })
    expect(botao(/Registrar estorno/)).toBeEnabled()
  })

  it('explicação de duas letras não serve — RN-M05 quer o motivo registrado', () => {
    render(<Estorno vm={vmEstorno()} />)
    fireEvent.click(primeiroRadio())
    fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: 'estorno' } })
    fireEvent.change(screen.getByLabelText('O que aconteceu'), { target: { value: 'ok' } })
    expect(botao(/Registrar estorno/)).toBeDisabled()
    expect(screen.getByText(/a auditoria vai ler depois/)).toBeInTheDocument()
  })

  it('lote sem nada estornável não mostra formulário', () => {
    render(<Estorno vm={vmEstorno({ lancamentos: [ENTRADA], total: 1 })} />)
    expect(screen.getByText(/Nenhum lançamento deste lote pode ser estornado/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Registrar estorno/ })).toBeNull()
  })
})

describe('movimento_descarte', () => {
  it('a dupla identificação é dita antes de preencher', () => {
    render(<Descarte vm={vmDescarte()} />)
    expect(screen.getByText(/gerente e o/)).toBeInTheDocument()
    expect(screen.getByText('duas pessoas')).toBeInTheDocument()
  })

  it('AC-6: lote liberado e válido não é selecionável, e diz por quê', () => {
    render(<Descarte vm={vmDescarte({ fila: [VENCIDO, LIBERADO], total: 2 })} />)
    const opcoes = radios()
    expect(opcoes).toHaveLength(2)
    expect(opcoes.filter((r) => r.disabled)).toHaveLength(1)
    expect(screen.getByText(/vencido ou bloqueado \(RN-L06\)/)).toBeInTheDocument()
  })

  it('AC-6: o alvo pedido que não pode ser descartado aparece com o impedimento', () => {
    render(<Descarte vm={vmDescarte({ alvo: LIBERADO })} />)
    expect(screen.getByText(/AMX2401/)).toBeInTheDocument()
  })

  it('AC-7: sem a segunda identificação o botão não envia', () => {
    render(<Descarte vm={vmDescarte()} />)
    fireEvent.click(primeiroRadio())
    fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: 'vencimento' } })
    fireEvent.change(screen.getByLabelText('Justificativa'), {
      target: { value: 'vencido na conferência do mês' },
    })
    expect(botao(/Registrar descarte/)).toBeDisabled()
    expect(screen.getByText(/Falta a segunda identificação/)).toBeInTheDocument()
  })

  it('AC-7: com a segunda identificação, envia — o par positivo', () => {
    render(<Descarte vm={vmDescarte()} />)
    fireEvent.click(primeiroRadio())
    fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: 'vencimento' } })
    fireEvent.change(screen.getByLabelText('Justificativa'), {
      target: { value: 'vencido na conferência do mês' },
    })
    fireEvent.change(screen.getByLabelText('Segunda identificação'), {
      target: { value: 'u-helena' },
    })
    expect(botao(/Registrar descarte/)).toBeEnabled()
  })

  it('o saldo aparece por lote: o descarte não é parcial', () => {
    render(<Descarte vm={vmDescarte()} />)
    expect(screen.getByText(/saldo 80/)).toBeInTheDocument()
  })

  it('fila vazia não vira formulário', () => {
    render(<Descarte vm={vmDescarte({ fila: [], total: 0 })} />)
    expect(screen.getByText(/Nenhum lote vencido ou bloqueado/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Registrar descarte/ })).toBeNull()
  })
})
