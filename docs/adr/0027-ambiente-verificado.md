# ADR-0027 — Conferir o `.env` contra o exemplo, por comando

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-08 |
| **Escopo** | Ferramental |

## Contexto

Acrescentar uma variável ao `.env.example` **não atualiza** o `.env` de quem já
rodou o projeto. A variável ausente cai no padrão do `docker-compose.yml`
(`${PROVEDOR:-openrouter}`), então tudo continua funcionando — e é justamente
por funcionar que o problema passa despercebido.

Aconteceu de verdade: depois de acrescentar o agnosticismo de provedor
([ADR-0025](./0025-agnosticismo-de-provedor.md)) e a observabilidade
([ADR-0026](./0026-observabilidade.md)), o `.env` da máquina estava sem **seis**
variáveis. O sistema rodava normalmente, e a pessoa não tinha como saber que
`PROVEDOR` existia — a opção estava lá e invisível.

Num projeto de portfólio isso é pior que um bug: quem clona não descobre metade
das capacidades porque elas não aparecem no arquivo que ele abre.

## Decisão

> **`make env` compara o `.env` com o `.env.example` e relata a diferença.
> `make env-completar` acrescenta as que faltam, com os valores do exemplo.**

Relata três coisas: variáveis do exemplo ausentes no `.env`, variáveis do `.env`
que não existem mais no exemplo, e variáveis importantes que estão vazias.

Deliberadamente **não** roda sozinho no boot: um script que edita o `.env` da
pessoa sem ela pedir é pior que a inconveniência que resolve.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Falhar o boot com variável faltando | O padrão do compose existe para o projeto subir sem configuração. Falhar contradiz `docker compose up` funcionar de cara |
| Regenerar o `.env` a cada `make up` | Apaga as chaves de quem já configurou. Inaceitável |
| Nada, e confiar no README | Foi o que havia, e falhou — seis variáveis invisíveis |
| Biblioteca de validação de ambiente | Peso desproporcional: o problema é comparar dois arquivos de chave=valor |

## Consequências

**Positivas**
- A capacidade nova fica visível para quem já tinha `.env`.
- `make env` vira o primeiro comando de diagnóstico quando algo não se comporta
  como a documentação diz.

**Negativas**
- Mais um script a manter, e ele conhece o formato do `.env` por regex — se o
  arquivo ganhar sintaxe (valores multi-linha, aspas), o script erra.
- `env-completar` acrescenta valores do exemplo, que são vazios para segredo.
  Não substitui ler o que foi acrescentado.

## Conformidade

- `make env` sai com relatório em vez de silêncio quando há divergência.
- `env-completar` **acrescenta**, nunca reescreve nem remove linha existente.

## Referências
- [ADR-0025](./0025-agnosticismo-de-provedor.md) · [ADR-0026](./0026-observabilidade.md)
