# T-048 — `RepoProduto.por_ean`: o leitor de código de barras tem para onde apontar

| | |
|---|---|
| **Onda** | W4 (destrava) |
| **Trilha** | A |
| **Tamanho** | P |
| **Tipo** | **Tarefa de contrato** — altera `CONTRATOS §4` |
| **Depende de** | T-007, T-036 |
| **Bloqueia** | **T-026** (AC-8), e a `US-02` inteira |
| **Regras** | RN-P01 |
| **Requisitos** | `RNF-02` · `US-02` |
| **Achado de origem** | [A-37](./ACHADOS.md) |

## Por que esta tarefa existe

A `US-02` é a história do conferente: *"preciso registrar o recebimento com o
leitor e uma mão livre"*. O `RNF-02` e o **AC-8 da T-026** exigem o fluxo
completo sem digitação, com código de barras.

**Um leitor devolve um EAN. E não existe caminho de EAN → produto em lugar
nenhum do sistema.**

```
RepoProduto (CONTRATOS §4, congelado)
    por_id(produto_id)   ← id interno, não EAN
    por_ids(ids)         ← idem
```

`ean` existe no tipo `Produto`, na coluna, no tradutor do repositório e no
viewmodel de `produto_ficha` — **nunca como critério de busca**. Não há `listar`
tampouco, então nem carregar um catálogo no cliente contorna.

Descoberto ao executar a T-026, que parou aqui em vez de improvisar: acrescentar
método a uma porta é alteração de contrato congelado, e o acordo de trabalho §8
manda parar.

## Por que é tarefa de contrato e **não** exige ADR

[CONTRATOS §11](./CONTRATOS.md) classifica as mudanças. Esta é a linha
*"`Permissao` nova → tarefa de contrato, rápida, mas serial"*: **aditiva**.
Nenhuma assinatura existente muda, nenhum chamador quebra, não há alternativa em
disputa — a alternativa (não ter busca por EAN) já foi rejeitada, porque é a
`US-02` deixando de existir.

ADR é para decisão com alternativas vivas. Aqui seria cerimônia.

## Arquivos de propriedade exclusiva

```
api/src/estoque/data/porta.py             (+1 método em RepoProduto)
api/src/estoque/data/repositorios.py      (+1 método em RepoProdutoSQL)
api/migrations/versions/0006_ean_unico.py
api/tests/registry/fakes.py               (+1 método em FakeRepoProduto)
api/tests/data/test_produto_por_ean.py
docs/tasks/CONTRATOS.md                   (§4 — nota de revisão)
```

> **Cruza arquivos de T-007 e T-036 de propósito.** É o que uma tarefa de
> contrato é: a alteração mora nos arquivos que o contrato descreve. O acordo de
> trabalho §4 só proíbe isso em **tarefa de feature** — e foi justamente por
> respeitar essa fronteira que a T-026 parou e abriu esta.

## Escopo

### Faz
- `RepoProduto.por_ean(ean, ctx) -> Produto | None` na porta.
- `RepoProdutoSQL.por_ean` no adaptador, com a **mesma omissão de custo** que
  `por_id` já aplica (`RN-A02`): quem não tem `custo.ler` recebe o campo ausente.
- `FakeRepoProduto.por_ean`, com o **mesmo comportamento** do real (achado A-11 —
  fake permissivo faz a suíte passar sobre um buraco).
- Migração `0006`: **`UNIQUE (produto.ean)`**. Sem ela `por_ean` não é bem
  definido — dois produtos com o mesmo EAN fariam a busca devolver "algum".
  Conferido no banco: 18 produtos, **zero duplicados**, então a restrição entra
  sem limpeza.

### Não faz
Busca por nome ou princípio ativo (não há requisito). `RepoUnidade` — a T-026
mostrou que o **comando** lê `unidade` direto por SQLAlchemy, o que é legítimo
(`commands/` pode; só `registry/` não pode), e não há AC pedindo o formulário
avisar antes.

## Critérios de aceite

- [x] **AC-1** `por_ean` devolve o produto do EAN pedido, e `None` para EAN que
      não existe.
      — e o casamento é por **igualdade**, não por prefixo: `ean[:-1]` e
      `ean + "0"` devolvem `None`. Ver "o teste que faltava", abaixo.
- [x] **AC-2** O custo chega **ausente** para quem não tem `custo.ler`, igual a
      `por_id`. *(negativo — `RN-A02`, `CA-05`)*
      — o método passa pelo mesmo `_para_produto` que `por_id`; a omissão vive
      no tradutor, num lugar só. O teste confere que o resto do produto continua
      chegando — sem isso, um `return None` faria o AC passar sem servir a nada.
- [x] **AC-3** O banco recusa dois produtos com o mesmo EAN. *(negativo — a
      restrição que torna `por_ean` bem definido)*
      — migração `0006`, `produto_ean_key`. Com o contraponto: EAN diferente
      entra normalmente, senão uma coluna quebrada que recusasse tudo passaria.
- [x] **AC-4** A **mesma bateria** roda contra o fake **e** contra o repositório
      real, e os dois concordam. *(achado A-11)*
      — `_bateria()` é chamada duas vezes. Sabotar o fake (ignorar `_visivel`)
      reprova só o lado do fake, que é o ponto do A-11.
- [x] **AC-5** `CONTRATOS §4` registra o método novo, com a nota de que a
      alteração é aditiva.

## O teste que faltava — registro

A primeira versão da bateria passava com o repositório **sabotado**: trocar
`ean == :ean` por `ean LIKE :ean || '%'` não reprovava nada, porque o "EAN
inexistente" do teste (`0000000000000`) não é prefixo de nenhum EAN real.

O par que faltava é `por_ean(ean[:-1])`. Um leitor que lesse mal o último dígito
devolveria **o produto errado** — e produto errado num recebimento é lote errado,
com validade e classe erradas, entrando em quarentena como se estivesse certo.

Fica registrado porque é a regra da casa mostrando o próprio valor: a sabotagem
foi feita, não foi pega, e o teste que faltava só apareceu por causa dela.

## Armadilhas

`por_ean` é a primeira busca do sistema por um identificador **externo**, que
vem do mundo físico e do leitor. Ele não é escopo de unidade — produto não
pertence a unidade (`RN-P01`) —, então não há interseção a aplicar aqui, e
inventar uma esconderia produto legítimo do conferente. O que continua valendo é
a omissão de custo, que é por ATOR e não por unidade.
