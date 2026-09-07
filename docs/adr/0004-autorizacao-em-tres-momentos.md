# ADR-0004 — Autorizar em três momentos, e confiar em apenas um

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-06 |
| **Escopo** | Fundacional |

## Contexto

Com o catálogo filtrado (ADR-0003) e o schema validado, é tentador concluir que a
autorização está resolvida. Não está. **O cliente pode montar um schema à mão e
enviar direto ao endpoint, sem passar pelo modelo.**

Validar apenas no momento em que o assistente responde é proteger o caminho errado.

## Decisão

> **Autorizar em três momentos, e tratar apenas o terceiro como garantia.**

| Quando | O quê | Protege contra |
|---|---|---|
| **Antes do modelo** | monta o catálogo filtrado pelo ator | o modelo propor o impossível |
| **Depois do modelo** | revalida o schema no servidor contra o mesmo catálogo | alucinação e requisição forjada |
| **Em cada `load` e cada `command`** | autoriza por registro, com a identidade real | **acesso indevido de fato** |

Os dois primeiros controlam o que é *oferecido*. O terceiro controla o que é
*acessível* — e é o único que protege.

Corolário: **schema recebido é payload não-confiável**, igual a qualquer body de
API. Nenhum tratamento especial por ter vindo do assistente.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Assinar o schema emitido pelo modelo e aceitar só schemas assinados | Impede forja, não impede abuso: o ator ainda pode reenviar schema legítimo de outro contexto. E não substitui autorização por registro |
| Autorizar só na borda HTTP, por rota | O componente é a unidade de acesso, não a rota. Um `load` pode tocar entidades de escopos diferentes |

## Consequências

**Positivas**
- A segurança não depende de o modelo estar bem comportado, nem de o cliente ser
  honesto.
- O mesmo código de autorização serve à tela tradicional e ao assistente.

**Negativas**
- Autorização repetida em todo `load` custa: mais consultas, mais latência.
- Disciplina permanente — um `load` novo escrito sem `requires` é uma brecha silenciosa.

**Riscos aceitos**
- Sobrecarga de checagem redundante. Aceita: o custo é baixo perto de um vazamento
  entre unidades.

## Conformidade

- `defineComponent` **exige** `requires`. O tipo não compila sem ele.
- `arch:check`: nenhum `load` acessa repositório sem receber `LoadContext`.
- Teste `CS-01`: schema forjado com componente fora do catálogo do ator é rejeitado
  no endpoint, sem o modelo no caminho.

## Referências
- [Arquitetura v2 §6](../03-arquitetura-v2.md) · `RN-A03`
