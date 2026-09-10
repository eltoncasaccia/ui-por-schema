/**
 * T-026 AC-8 — o fluxo é executável **sem digitação**, com o leitor. `RNF-02`.
 *
 * A história é a da Cleide: *"preciso registrar o recebimento com o leitor e uma
 * mão livre"*. Um leitor USB se comporta como teclado — ele **digita os dígitos
 * e aperta Enter**. É exatamente isso que estes testes fazem, com `fireEvent`;
 * `@testing-library/user-event` não está no projeto, e acrescentar dependência
 * é decisão que se pergunta antes (ADR-0028).
 *
 * O que precisa ser verdade para a mão livre existir:
 *
 *   1. o campo de scan tem o foco ao abrir — senão a primeira caixa se perde;
 *   2. Enter no scan **acrescenta o item**, sem clique;
 *   3. Enter no scan **não envia o formulário** — senão a primeira caixa lida
 *      gravaria um recebimento de um item só;
 *   4. o foco **volta** para o scan — senão a segunda caixa cai noutro campo.
 *
 * O item 4 é o que separa "funciona na demonstração" de "funciona na esteira".
 */
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ViewModel } from '../generated/componentes'
import { view as Formulario } from '../views/recebimento_registrar'

type VM = ViewModel<'recebimento_registrar'>

const EAN = '7891234000018'

function vm(over: Partial<VM> = {}): VM {
  return {
    unidades: [
      { id: 'cd-matriz', nome: 'CD Matriz' },
      { id: 'cd-refrigerado', nome: 'CD Refrigerado' },
    ],
    unidade_sugerida: 'cd-matriz',
    validade_minima_dias: 180,
    obrigatorios_do_item: ['numero', 'fabricacao', 'validade'],
    lido: null,
    ean_nao_encontrado: null,
    ...over,
  }
}

const LIDO: NonNullable<VM['lido']> = {
  produto_id: 'p-amox',
  ean: EAN,
  nome: 'Amoxicilina 500mg',
  fabricante: 'Medquimica',
  classe: 'comum',
  exige_temperatura: false,
  exige_rt: false,
}

function campoScan(): HTMLElement {
  return screen.getByLabelText('Código de barras do produto')
}

/** O que o leitor faz: preenche o campo e dispara Enter. Nenhum clique. */
function bipar(ean: string) {
  const campo = campoScan()
  fireEvent.change(campo, { target: { value: ean } })
  fireEvent.keyDown(campo, { key: 'Enter' })
}

describe('AC-8 · o leitor de código de barras', () => {
  it('o campo de scan tem o foco ao abrir', () => {
    render(<Formulario vm={vm()} />)
    expect(document.activeElement).toBe(campoScan())
  })

  it('bipar acrescenta o item, sem nenhum clique', () => {
    render(<Formulario vm={vm({ lido: LIDO })} />)
    expect(screen.queryByLabelText(/Número do lote/)).toBeNull()

    bipar(EAN)

    expect(screen.getByText(/Amoxicilina 500mg/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Número do lote/)).toBeInTheDocument()
  })

  it('o foco volta para o scan depois de acrescentar', () => {
    // Item 4: sem isto, a segunda caixa da esteira cai num campo de data.
    render(<Formulario vm={vm({ lido: LIDO })} />)
    bipar(EAN)
    expect(document.activeElement).toBe(campoScan())
  })

  it('Enter no scan NÃO envia o formulário', () => {
    // O par negativo do item 3. Se o botão fosse `submit`, a primeira leitura
    // gravaria um recebimento de um item só — e o conferente só descobriria
    // depois de bipar a caixa seguinte.
    render(<Formulario vm={vm({ lido: LIDO })} />)
    const enviar = screen.getByRole('button', { name: /Confirmar recebimento/ })
    expect(enviar).toHaveAttribute('type', 'button')
    bipar(EAN)
    expect(enviar).toBeDisabled()
  })

  it('bipar um EAN que não é o resolvido não acrescenta nada', () => {
    // A tela não adivinha: só acrescenta o produto que o SERVIDOR resolveu para
    // aquele código. Sem esta guarda, uma leitura suja viraria o item anterior.
    render(<Formulario vm={vm({ lido: LIDO })} />)
    bipar('9999999999999')
    expect(screen.queryByLabelText(/Número do lote/)).toBeNull()
  })

  it('EAN desconhecido avisa e deixa o operador seguir', () => {
    render(<Formulario vm={vm({ ean_nao_encontrado: '0000000000000' })} />)
    expect(screen.getByText(/Nenhum produto com o código/)).toBeInTheDocument()
    // Continua sendo possível trabalhar: o campo de scan segue disponível.
    expect(campoScan()).toBeEnabled()
  })
})

describe('o que a classe do produto exige', () => {
  it('termolábil pede a temperatura de chegada — RN-F01', () => {
    render(<Formulario vm={vm({ lido: { ...LIDO, classe: 'termolabil', exige_temperatura: true } })} />)
    bipar(EAN)
    expect(screen.getByLabelText(/Temperatura de chegada/)).toBeInTheDocument()
  })

  it('controlado pede a segunda identificação — RN-R05', () => {
    render(<Formulario vm={vm({ lido: { ...LIDO, classe: 'controlado', exige_rt: true } })} />)
    bipar(EAN)
    expect(screen.getByLabelText(/responsável técnico/i)).toBeInTheDocument()
  })

  it('produto comum não pede nenhum dos dois', () => {
    // O par negativo: sem ele, campos sempre visíveis passariam nos dois testes
    // acima e a tela pediria temperatura de caixa de dipirona.
    render(<Formulario vm={vm({ lido: LIDO })} />)
    bipar(EAN)
    expect(screen.queryByLabelText(/Temperatura de chegada/)).toBeNull()
    expect(screen.queryByLabelText(/responsável técnico/i)).toBeNull()
  })
})

describe('a tela avisa antes de o servidor recusar', () => {
  it('divergência entre físico e nota aparece na hora, e não bloqueia', () => {
    render(<Formulario vm={vm({ lido: LIDO })} />)
    bipar(EAN)
    fireEvent.change(screen.getByLabelText(/Quantidade física/), { target: { value: '8' } })
    fireEvent.change(screen.getByLabelText(/Quantidade na nota/), { target: { value: '10' } })

    expect(screen.getByText('divergência')).toBeInTheDocument()
    expect(screen.getByText(/não impede a conclusão/)).toBeInTheDocument()
  })

  it('validade curta pede a autorização do RT — RN-L07', () => {
    render(<Formulario vm={vm({ lido: LIDO })} />)
    bipar(EAN)
    const daquiADias = (d: number) =>
      new Date(Date.now() + d * 86_400_000).toISOString().slice(0, 10)
    fireEvent.change(screen.getByLabelText(/Validade de/), {
      target: { value: daquiADias(60) },
    })
    expect(screen.getByText('validade curta')).toBeInTheDocument()
    expect(screen.getByLabelText(/Autorização expressa do RT/)).toBeInTheDocument()
  })

  it('validade folgada não pede autorização nenhuma', () => {
    render(<Formulario vm={vm({ lido: LIDO })} />)
    bipar(EAN)
    const daquiADias = (d: number) =>
      new Date(Date.now() + d * 86_400_000).toISOString().slice(0, 10)
    fireEvent.change(screen.getByLabelText(/Validade de/), {
      target: { value: daquiADias(400) },
    })
    expect(screen.queryByText('validade curta')).toBeNull()
  })
})
