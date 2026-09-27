# A-004 — A regra do e2e está certa? O experimento

| | |
|---|---|
| **Data** | 2026-09-27 |
| **Produzido por** | experimento pedido pelo dono, fora do board |
| **Pergunta** | O `web/CLAUDE.md` afirma: *"repetir no navegador um teste que o `vitest` já faz é custo sem evidência nova"*. Isso se sustenta? |
| **Método** | Escrever de propósito os testes que a regra proíbe — fluxos de escrita já cobertos por `vitest` e `pytest` — e **contar defeitos encontrados**. Dois alvos: saída (`/saida`) e recebimento (`/recebimento/novo`) |
| **Resultado** | **A regra está errada.** Dois alvos, **dois defeitos**, ambos invisíveis às camadas existentes. Um deles fecha a tela principal do conferente ([A-53](../tasks/ACHADOS.md)) |
| **Recomendação** | Emendar a regra, não revogá-la. O corte certo não é "navegador × outras camadas" — é **"viewmodel de verdade × viewmodel escrito à mão"** (§3) |

> **O custo, para quem for julgar o resultado:** 4 testes novos, +3 s de suíte,
> uma tarde. Se o experimento tivesse dado empate, este relatório diria isso, e
> os arquivos teriam sido apagados.

---

## 1. Placar

| Alvo | Cobertura existente | e2e novo | Defeito encontrado |
|---|---|---|---|
| **Saída com FEFO** | `comando.test.tsx` (6 testes sobre este comando), `pytest` do comando | 3 testes | [A-52](../tasks/ACHADOS.md) — botão habilitado com cliente e nota vazios; `422` genérico **depois** da confirmação |
| **Recebimento** | `recebimento_registrar.test.tsx` (12 testes), `pytest` do comando | 1 teste | [A-53](../tasks/ACHADOS.md) — **o leitor de código de barras não resolve produto nenhum.** A tela não recebe |

Dois de dois. E o segundo não é detalhe de formulário: é a tela que o `RNF-02`
chama de caminho principal do conferente, entregue, marcada ✅, e **inutilizável**.

---

## 2. Por que as outras camadas não viram

As duas causas são a mesma, e não têm a ver com navegador.

### O `vitest` testa o viewmodel que o autor do teste imaginou

Em `comando.test.tsx:183`, a lista de motivos da fixture é:

```ts
{ valor: 'avaria', rotulo: 'Avaria', exige_destinatario: false }
```

**Todo motivo da fixture tem `exige_destinatario: false`.** No servidor de
verdade, `venda` — o motivo mais comum de uma distribuidora — tem `true`. O
caminho do A-52 nunca foi exercido porque o autor do teste não o escreveu na
fixture, e nada obriga a fixture a cobrir o domínio real.

O e2e não escolhe o viewmodel: ele recebe o que o registry produz contra o seed.

### O `vitest` não exercita a volta entre view e servidor

`recebimento_registrar.test.tsx` renderiza `<Formulario vm={...}>` com `lido`
já preenchido. Os 12 testes provam que o formulário **desenha** certo o produto
lido — validade curta, termolábil, controlado, tudo. Nenhum deles pode provar
que alguma coisa **consegue ler** o produto, porque a leitura acontece fora do
componente.

E é exatamente ali que estava o furo: a view escreve `data-ean` no campo, o
comentário dela promete que *"o componente repede os próprios dados com
`ean=<lido>`"*, e **ninguém lê esse atributo**. A rota manda
`params: () => ({})`. A ponta nunca foi ligada.

> A `auditar-testes` deste projeto já nomeia essa família: *"os fakes
> divergiram do adaptador real"*. O que este experimento mostra é que ela não
> se limita a adaptadores — **um viewmodel escrito à mão é um fake**, e
> diverge do mesmo jeito.

---

## 3. A emenda que a regra pede

O texto atual de [`web/CLAUDE.md`](../../web/CLAUDE.md):

> O e2e cobre **só** o que as outras camadas não alcançam: roteamento real,
> cookie de sessão pelo proxy, e o menu filtrado pelo catálogo do ator. Repetir
> no navegador um teste que o `vitest` já faz é custo sem evidência nova.

A intenção está certa — suíte de navegador é lenta e frágil, e duplicar por
duplicar é desperdício. O critério é que está errado. Proposta:

> O e2e cobre o que as outras camadas não alcançam. **Toda tela cujo viewmodel
> vem do servidor tem pelo menos um caminho exercido de ponta a ponta contra o
> seed**, porque `vitest` só vê o viewmodel que a fixture escreveu — e fixture
> é fake. Repetir no navegador uma asserção de *desenho* (rótulo, ordem,
> formatação) continua sendo custo sem evidência nova.

O corte não é por camada. É por **origem do dado**: uma vez por tela, com o
viewmodel de verdade.

Custo de aplicar: as telas com viewmodel do servidor e escrita são seis. Três já
têm (quarentena pela T-057, saída e recebimento por este experimento). Faltam
estorno, descarte e autorização de controlado — e as duas primeiras **não têm
rota**, só nascem por composição do assistente, que o e2e não tem
([ADR-0013](../adr/0013-suite-de-avaliacao.md): sem chave de provedor). Isso é
uma lacuna de desenho da suíte, e fica registrada aqui.

---

## 4. O A-53 — como foi corrigido

O relatório original listava três saídas e recomendava mover o campo de scan
para fora da view (opção A, no padrão do `TelaSaida.tsx`). **Ao implementar,
ela se mostrou errada**, e vale registrar por quê: mover o campo levaria junto
o `autoFocus` e o Enter que fecham o laço do leitor USB, e quebraria os 12
testes do `vitest` que afirmam o campo dentro da view. O padrão do `TelaSaida`
serve para param pedido **uma vez, antes** da tela existir — aqui são dez
leituras no meio do preenchimento.

O caminho certo já estava no projeto, escrito pela T-049 para o problema
gêmeo. [`render/comando.ts`](../../web/src/render/comando.ts) diz, no próprio
cabeçalho: *"`View<Id>` continua `(props: { vm }) => JSX.Element`: a view não
ganha prop novo, não importa `api`, não sabe que existe rede. Ela só despacha
um `CustomEvent`"*.

Foi o que se fez, para leitura em vez de escrita:

| Peça | Papel |
|---|---|
| [`render/repedir.ts`](../../web/src/render/repedir.ts) | o canal: a view despacha `repedir` com os params que ela mudou |
| [`app/telas/TelaRecebimento.tsx`](../../web/src/app/telas/TelaRecebimento.tsx) | ouve o evento e é dona do param — a view segue sem saber que rede existe |
| `views/recebimento_registrar.tsx` | troca o `data-ean` morto pelo despacho; campo, foco e Enter ficam onde estavam |

**O contrato de view (CONTRATOS §6) não mudou**, e por isso isto não pediu ADR.

### O segundo defeito, que só apareceu ao ligar o primeiro

Com o param funcionando, a tela passou a **perder a lista de itens a cada caixa
lida**. Causa: params novos dão `queryKey` nova, a query volta a `isPending`, o
`Esqueleto` entra no lugar da view, e o estado local dela morre com o
desmonte.

Isso **não era do recebimento** — é de todo componente com param interativo. O
filtro interativo da [T-055](../tasks/PROGRESSO.md) cairia exatamente no mesmo
buraco, e ninguém teria ligado uma coisa à outra. Resolvido com
`placeholderData` em `motor.tsx`, servindo o dado anterior enquanto o novo vem.

E aí um terceiro, que a suíte pegou na hora: manter o dado anterior ao trocar
de **rota** entregava a carga de `recebimento_registrar` à view de `lote_lista`,
que quebra ao ler um campo inexistente. O teste de popstate
(`rotas_operacao.test.tsx`, AC-6) ficou vermelho, e o `placeholderData` passou a
valer só para o **mesmo** componente.

> Três defeitos encadeados, e o primeiro estava entregue e marcado ✅ havia
> semanas. É o argumento do §3 em forma de história.

## 5. O que este experimento não fez

- **Não mediu fragilidade.** A objeção mais forte à suíte de navegador é teste
  intermitente, e quatro testes numa tarde não dizem nada sobre isso. A regra
  atual pode estar defendendo contra um custo que este relatório não mediu.
- **Não cobriu estorno, descarte e controlados** — os dois primeiros por falta
  de rota (§3), o terceiro por tempo.
- **Não corrigiu o A-53** (§4).
- **Não olhou o `pytest` com a mesma lente.** Os fakes do lado Python têm o
  mesmo risco de divergir do registry real, e ninguém mediu.
