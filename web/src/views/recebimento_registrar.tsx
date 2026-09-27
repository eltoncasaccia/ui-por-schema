import { useRef, useState } from 'react'
import { dispararComando } from '../render/comando'
import { dispararRepedir } from '../render/repedir'
import { Etiqueta } from '../ui/Etiqueta'
import type { Tom } from '../ui/estados'
import type { View } from './tipos'
import type { ViewModel } from '../generated/componentes'

type VM = ViewModel<'recebimento_registrar'>
type Lido = NonNullable<VM['lido']>

/** Uma linha da nota, no estado em que a tela a mantém antes de enviar. */
interface Item {
  chave: string
  produto_id: string
  rotulo: string
  classe: Lido['classe'] | null
  numero: string
  fabricacao: string
  validade: string
  quantidade: string
  quantidade_nota: string
}

const CLASSE: Record<Lido['classe'], { rotulo: string; tom: Tom }> = {
  comum: { rotulo: 'Comum', tom: 'neutro' },
  controlado: { rotulo: 'Controlado', tom: 'laranja' },
  termolabil: { rotulo: 'Termolábil', tom: 'ciano' },
  antimicrobiano: { rotulo: 'Antimicrobiano', tom: 'ambar' },
}

function vazio(produto_id: string, rotulo: string, classe: Lido['classe'] | null): Item {
  return {
    chave: crypto.randomUUID(),
    produto_id,
    rotulo,
    classe,
    numero: '',
    fabricacao: '',
    validade: '',
    quantidade: '',
    quantidade_nota: '',
  }
}

function diasAte(iso: string): number | null {
  if (!iso) return null
  const ms = new Date(`${iso}T00:00:00`).getTime() - Date.now()
  return Number.isNaN(ms) ? null : Math.floor(ms / 86_400_000)
}

/**
 * O primeiro formulário de escrita, e a tela do conferente.
 *
 * **O leitor de código de barras é o caminho principal, não um atalho**
 * (`RNF-02`, AC-8). O campo de scan recebe o foco ao abrir e o recupera depois
 * de cada leitura, porque um leitor USB **digita e aperta Enter** — se o foco
 * sair, a segunda caixa lida vai parar num campo qualquer. Por isso também o
 * `Enter` no scan não envia o formulário: envia o scan.
 *
 * A resolução do EAN não acontece aqui. O componente repede os próprios dados
 * com `ean=<lido>` e o servidor responde com o produto (`RepoProduto.por_ean`,
 * T-048) — a view recebe `vm.lido` pronto e não conhece a API (ADR-0007).
 *
 * **A tela avisa; o servidor recusa.** `exige_temperatura`, `exige_rt` e
 * `validade_minima_dias` chegam calculados do servidor, e são repetidos lá no
 * comando (`RN-F01`, `RN-R05`, `RN-L07`). Aqui eles existem para o formulário
 * não pedir errado — não para garantir nada (ADR-0004).
 */
export const view: View<'recebimento_registrar'> = ({ vm }) => {
  const [unidade, setUnidade] = useState(vm.unidade_sugerida ?? vm.unidades[0]?.id ?? '')
  const [notaFiscal, setNotaFiscal] = useState('')
  const [fornecedor, setFornecedor] = useState('')
  const [itens, setItens] = useState<Item[]>([])
  const [temperatura, setTemperatura] = useState('')
  const [rt, setRt] = useState('')
  const [autorizacao, setAutorizacao] = useState('')
  const [scan, setScan] = useState('')
  const campoScan = useRef<HTMLInputElement>(null)

  // O produto que o servidor resolveu na última leitura ainda não virou linha?
  const pendente = vm.lido && !itens.some((i) => i.produto_id === vm.lido?.produto_id)

  function acrescentar(l: Lido) {
    setItens((atuais) => [...atuais, vazio(l.produto_id, `${l.nome} · ${l.fabricante}`, l.classe)])
    setScan('')
    // Devolve o foco ao scan: o leitor dispara sozinho na próxima caixa.
    campoScan.current?.focus()
  }

  function alterar(chave: string, campo: keyof Item, valor: string) {
    setItens((atuais) =>
      atuais.map((i) => (i.chave === chave ? { ...i, [campo]: valor } : i)),
    )
  }

  const classes = new Set(itens.map((i) => i.classe))
  const exigeTemperatura = classes.has('termolabil')
  const exigeRt = classes.has('controlado')
  const curtos = itens.filter((i) => {
    const d = diasAte(i.validade)
    return d !== null && d < vm.validade_minima_dias
  })

  const completos = itens.every(
    (i) => i.numero && i.fabricacao && i.validade && Number(i.quantidade) > 0,
  )
  const podeEnviar =
    Boolean(unidade) &&
    notaFiscal.trim().length > 0 &&
    fornecedor.trim().length > 0 &&
    itens.length > 0 &&
    completos &&
    (!exigeTemperatura || temperatura !== '') &&
    (!exigeRt || rt.trim().length > 0) &&
    (curtos.length === 0 || autorizacao.trim().length >= 10)

  return (
    <section className="cartao">
      <div className="cartao-cabeca">
        <span className="titulo-painel">Registrar recebimento</span>
        <span className="mono fraco" style={{ fontSize: 11 }}>
          {itens.length} {itens.length === 1 ? 'item' : 'itens'}
        </span>
      </div>

      <div className="cartao-corpo">
        {/* ---------------------------------------------- etapa 1 · a nota */}
        <div className="linha-cartao-campos">
          <label>
            <div className="campo-rotulo">Unidade de destino</div>
            <select
              className="campo"
              value={unidade}
              onChange={(e) => setUnidade(e.target.value)}
            >
              {vm.unidades.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nome}
                </option>
              ))}
            </select>
          </label>
          <label>
            <div className="campo-rotulo">Nota fiscal</div>
            <input
              className="campo"
              value={notaFiscal}
              onChange={(e) => setNotaFiscal(e.target.value)}
            />
          </label>
          <label>
            <div className="campo-rotulo">Fornecedor</div>
            <input
              className="campo"
              value={fornecedor}
              onChange={(e) => setFornecedor(e.target.value)}
            />
          </label>
        </div>

        {/* --------------------------------------- etapa 2 · itens, pelo leitor */}
        <div style={{ marginTop: 16 }}>
          <label>
            <div className="campo-rotulo">Código de barras</div>
            <input
              ref={campoScan}
              className="campo mono"
              // `autoFocus` é o oposto de um antipadrão aqui: o leitor USB
              // digita e aperta Enter assim que a caixa passa, e sem foco a
              // leitura cai em campo nenhum. É a tela que existe para ser usada
              // com as duas mãos ocupadas (`RNF-02`).
              autoFocus
              inputMode="numeric"
              placeholder="dispare o leitor"
              aria-label="Código de barras do produto"
              value={scan}
              onChange={(e) => setScan(e.target.value)}
              onKeyDown={(e) => {
                // O leitor termina com Enter. Aqui ele confirma a LEITURA, e
                // nunca envia o formulário — senão a primeira caixa lida
                // gravaria um recebimento de um item só.
                if (e.key !== 'Enter') return
                e.preventDefault()
                // Já resolvido: o segundo Enter acrescenta. É o que fecha o
                // laço do leitor USB sem tirar a mão do teclado.
                if (vm.lido && vm.lido.ean === scan) {
                  acrescentar(vm.lido)
                  return
                }
                // Ainda não resolvido: pede ao servidor. Antes do A-53 isto
                // era um atributo `data-ean` que ninguém lia, e o leitor não
                // resolvia produto nenhum.
                if (scan.trim()) dispararRepedir(e.currentTarget, { params: { ean: scan.trim() } })
              }}
            />
          </label>

          {vm.ean_nao_encontrado && (
            <p className="fraco" style={{ fontSize: 12, margin: '6px 0 0' }}>
              Nenhum produto com o código <span className="mono">{vm.ean_nao_encontrado}</span>.
              Confira a leitura ou informe o produto manualmente.
            </p>
          )}

          {pendente && vm.lido && (
            <p style={{ fontSize: 13, margin: '8px 0 0' }}>
              <button type="button" className="btn" onClick={() => acrescentar(vm.lido!)}>
                Acrescentar {vm.lido.nome}
              </button>{' '}
              <Etiqueta tom={CLASSE[vm.lido.classe].tom}>
                {CLASSE[vm.lido.classe].rotulo}
              </Etiqueta>
            </p>
          )}
        </div>

        {itens.length === 0 ? (
          <p className="vazio" style={{ marginTop: 12 }}>
            Nenhum item ainda. Dispare o leitor na primeira caixa.
          </p>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: '12px 0 0' }}>
            {itens.map((i) => (
              <li key={i.chave} className="linha-cartao" style={{ marginTop: 8 }}>
                <div className="linha-cartao-topo">
                  <span style={{ fontWeight: 500, fontSize: 13 }}>{i.rotulo}</span>
                  {i.classe && (
                    <Etiqueta tom={CLASSE[i.classe].tom}>{CLASSE[i.classe].rotulo}</Etiqueta>
                  )}
                </div>
                <div className="linha-cartao-campos">
                  {/* RN-L01: os três não são opcionais em lote nenhum. */}
                  <label>
                    <div className="campo-rotulo">Lote</div>
                    <input
                      className="campo mono"
                      aria-label={`Número do lote de ${i.rotulo}`}
                      value={i.numero}
                      onChange={(e) => alterar(i.chave, 'numero', e.target.value)}
                    />
                  </label>
                  <label>
                    <div className="campo-rotulo">Fabricação</div>
                    <input
                      type="date"
                      className="campo"
                      aria-label={`Fabricação de ${i.rotulo}`}
                      value={i.fabricacao}
                      onChange={(e) => alterar(i.chave, 'fabricacao', e.target.value)}
                    />
                  </label>
                  <label>
                    <div className="campo-rotulo">Validade</div>
                    <input
                      type="date"
                      className="campo"
                      aria-label={`Validade de ${i.rotulo}`}
                      value={i.validade}
                      onChange={(e) => alterar(i.chave, 'validade', e.target.value)}
                    />
                  </label>
                  <label>
                    <div className="campo-rotulo">Qtd. física</div>
                    <input
                      type="number"
                      min={1}
                      className="campo"
                      aria-label={`Quantidade física de ${i.rotulo}`}
                      value={i.quantidade}
                      onChange={(e) => alterar(i.chave, 'quantidade', e.target.value)}
                    />
                  </label>
                  <label>
                    <div className="campo-rotulo">Qtd. na nota</div>
                    <input
                      type="number"
                      min={1}
                      className="campo"
                      aria-label={`Quantidade na nota de ${i.rotulo}`}
                      value={i.quantidade_nota}
                      onChange={(e) => alterar(i.chave, 'quantidade_nota', e.target.value)}
                    />
                  </label>
                </div>
                {/* RN-R04: a divergência aparece na hora, e NÃO impede. */}
                {i.quantidade_nota !== '' && i.quantidade_nota !== i.quantidade && (
                  <p style={{ fontSize: 12, margin: '6px 0 0' }}>
                    <Etiqueta tom="ambar">divergência</Etiqueta>{' '}
                    <span className="fraco">
                      gera pendência vinculada, e não impede a conclusão.
                    </span>
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}

        {/* ------------------------------------------ etapa 3 · conferência */}
        {(exigeTemperatura || exigeRt || curtos.length > 0) && (
          <div className="linha-cartao-campos" style={{ marginTop: 16 }}>
            {/* RN-F01 */}
            {exigeTemperatura && (
              <label>
                <div className="campo-rotulo">Temperatura de chegada (°C)</div>
                <input
                  type="number"
                  step="0.1"
                  className="campo"
                  aria-label="Temperatura de chegada da carga"
                  value={temperatura}
                  onChange={(e) => setTemperatura(e.target.value)}
                />
              </label>
            )}
            {/* RN-R05: a segunda identificação, e são duas pessoas. */}
            {exigeRt && (
              <label>
                <div className="campo-rotulo">Responsável técnico</div>
                <input
                  className="campo"
                  aria-label="Identificação do responsável técnico"
                  value={rt}
                  onChange={(e) => setRt(e.target.value)}
                />
              </label>
            )}
          </div>
        )}

        {/* RN-L07: o aviso aparece ao lado da decisão, não no fim. */}
        {curtos.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <p style={{ fontSize: 13, margin: '0 0 6px' }}>
              <Etiqueta tom="laranja">validade curta</Etiqueta>{' '}
              <span className="fraco">
                {curtos.length} {curtos.length === 1 ? 'item vence' : 'itens vencem'} em menos
                de {Math.round(vm.validade_minima_dias / 30)} meses. Exige autorização expressa
                do RT.
              </span>
            </p>
            <label>
              <div className="campo-rotulo">Autorização do RT</div>
              <input
                className="campo"
                aria-label="Autorização expressa do RT para validade curta"
                value={autorizacao}
                onChange={(e) => setAutorizacao(e.target.value)}
              />
            </label>
          </div>
        )}

        {/* ----------------------------------------- etapa 4 · confirmação */}
        <div style={{ marginTop: 16 }}>
          <button type="button" className="btn btn-primario" disabled={!podeEnviar}
            onClick={(e) => {
              dispararComando(e.currentTarget, {
                acao: 'recebimento_registrar',
                corpo: {
                  unidade_id: unidade,
                  nota_fiscal: notaFiscal,
                  fornecedor,
                  itens: itens.map((i) => ({
                    produto_id: i.produto_id,
                    numero: i.numero,
                    fabricacao: i.fabricacao,
                    validade: i.validade,
                    quantidade: Number(i.quantidade),
                    quantidade_nota: i.quantidade_nota ? Number(i.quantidade_nota) : null,
                  })),
                  temperatura_chegada_c: exigeTemperatura ? Number(temperatura) : null,
                  rt_id: exigeRt ? rt : null,
                  autorizacao_validade_rt: curtos.length > 0 ? autorizacao : null,
                },
              })
            }}>
            Confirmar recebimento
          </button>
          <p className="fraco" style={{ fontSize: 12, margin: '8px 0 0' }}>
            Todo lote entra em <strong>quarentena</strong>. A liberação é decisão do
            responsável técnico, em outra tela.
          </p>
        </div>
      </div>
    </section>
  )
}
