# ADR-0010 — Deixar contagem, ajuste e transferência fora do ciclo 1

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-09-07 |
| **Escopo** | Ciclo 1 |

## Contexto

O ciclo 1 precisa provar escrita e permissão reais (ADR-0002, ADR-0004) e responder
a pergunta em aberto sobre taxa de schema válido. Precisa também caber num ciclo.

Contagem de inventário é o fluxo de maior valor aparente — a divergência de 3,8% foi
um dos episódios que motivaram o projeto. Também é o fluxo mais caro.

## Decisão

> **Contagem, inventário, ajuste de saldo e transferência entre unidades ficam
> fora do ciclo 1.**

O que decidiu foi a conferência dos oito critérios de aceite, um a um: **nenhum
depende dos três fluxos cortados.** CA-02 é satisfeito por `RN-M06` (saldo é a soma
dos movimentos), não por contagem — contagem *detecta* divergência, o razão
imutável a *previne*.

Ajuste cai por consequência de regra, não por escolha: `RN-I05` diz que nenhum
ajuste ocorre sem contagem aprovada por trás.

## Por que contagem é o pior primeiro fluxo

Acumula as quatro dificuldades que a arquitetura manda evitar no início:

1. É multi-etapa com validação cruzada → é L1 por ADR-0005 → **ensina pouco** sobre
   a hipótese de composição, que é o que o ciclo 1 existe para testar.
2. Exige off-line (`RNF-03`), que colide com catálogo servido pelo servidor (ADR-0003).
3. Tem conflito distribuído real: dois usuários contando o mesmo endereço sem
   conexão. Isso é problema de merge, não de CRUD.
4. Depende de duas decisões do cliente ainda não tomadas (pendências 4 e 5 do
   documento 02).

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Contagem on-line apenas, off-line no ciclo 2 | Meia contagem não fecha o ciclo operacional; Uberlândia é justamente quem mais conta |
| Ajuste avulso sem contagem | Viola `RN-I05` diretamente |
| Cortar controlados no lugar | `CA-04` é o teste mais afiado do ADR-0002. Cortá-lo esvaziaria o release |

## Consequências

**Positivas**
- Os oito critérios de aceite permanecem no escopo. O corte é grande e não custa
  critério nenhum.
- **As cinco pendências do documento 02 deixam de bloquear** — todas caem dentro do
  que saiu. Viram critério de entrada do ciclo 2.
- Off-line sai junto, com ele o item técnico mais espinhoso (ADR-0015).

**Negativas**
- O cliente não vê resolvido o episódio da divergência de 3,8% neste ciclo. É a
  conversa de expectativa mais difícil deste PRD.
- **O componente de exemplo da arquitetura, `lote_ajuste_form`, não faz parte do
  ciclo 1.** Continua sendo o exemplo certo do contrato; só não é o primeiro a ser
  escrito.

**Riscos aceitos**
- Modelar contagem depois pode revelar necessidade de mudança no razão de
  movimentos. Mitigação: `RN-M06` já força saldo derivado, que é a propriedade de
  que a contagem precisa.

## Conformidade

- Teste de escopo: nenhum componente registrado no ciclo 1 tem id em
  `{contagem*, ajuste*, transferencia*}`.

## Referências
- [Escopo do ciclo 1](../04-escopo-ciclo-1.md) · [PRD-001 §3.1](../prd/PRD-001-ciclo-1.md)
