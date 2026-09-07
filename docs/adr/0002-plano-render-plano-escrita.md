# ADR-0002 — Separar plano de render e plano de escrita

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-06 |
| **Escopo** | Fundacional |

## Contexto

A v1 era 100% leitura e sem autenticação. A v2 existe para responder se CRUD real
é viável com uma IA compondo a tela. A objeção óbvia: se o modelo escolhe o que
aparece, ele acaba influenciando o que é gravado.

## Decisão

> **A saída do modelo autoriza renderizar. Nunca autoriza escrever.**

```
PLANO DE RENDER     modelo → schema (nomes + params) → valida → desenha
PLANO DE ESCRITA    humano → submit → endpoint autenticado → domínio → banco
```

O modelo vive inteiro no primeiro plano. Ele pode pedir *"mostre o formulário de
liberação do lote L-8842"* — isso é render. Quem grava é a pessoa que clica em
salvar, passando pelo **mesmo endpoint autenticado** que a tela tradicional usa.

**Renderizar um formulário não é escrever.**

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Modelo dispara comandos com confirmação do usuário | A confirmação vira carimbo. O usuário confirma o que não leu, e a responsabilidade fica ambígua |
| Modelo propõe payload de escrita, humano edita | O payload proposto ancora a decisão. Um número alucinado com cara de sugestão é pior que nenhum |
| Modelo escreve com permissões reduzidas | Não existe permissão reduzida para escrita de estoque regulado. `RN-C01` exige identidade humana nominal |

## Consequências

**Positivas**
- CRUD vira viável sem entregar o banco ao modelo.
- Um único caminho de escrita, auditado igual, venha da tela ou do assistente.
- `RN-D01` (auditoria com autor) continua verdadeiro sem caso especial.

**Negativas**
- O assistente não automatiza operação. Ele não é agente; é superfície de consulta
  e de navegação para formulário. Expectativa a gerenciar com o cliente.
- Fluxos de várias etapas não ganham nada com o assistente — ver ADR-0005.

**Riscos aceitos**
- Usuário pode interpretar o assistente como capaz de agir e frustrar-se. Mitigado
  em texto de interface, não em arquitetura.

## Conformidade

- Nenhum `command` é invocável a partir do pipeline do assistente. Teste: percorrer
  o registry e afirmar que nenhum caminho de código liga a saída do modelo a um
  `CommandDef`.
- `arch:check` proíbe `application/assistant/**` de importar `application/commands/**`.

## Referências
- [Arquitetura v2 §2 e §7](../03-arquitetura-v2.md)
