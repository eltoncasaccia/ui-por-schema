---
name: auditar-testes
description: Audita a qualidade da suíte de testes — cobertura de critérios de aceite, existência de testes negativos, testes que pulam em silêncio, fakes que divergiram do adaptador real, asserções fracas e acoplamento ao relógio. Use antes de fechar uma onda, ao desconfiar de suíte verde que não prova nada, ou depois de acrescentar muitos testes de uma vez. Complementa auditar-execucao, que olha documento contra código.
---

# Auditar os testes

Suíte verde não é evidência. Esta skill pergunta uma coisa: **se alguém
quebrasse a regra, algum teste ficaria vermelho?**

Complementa `auditar-execucao`. Aquela pergunta se o documento diz a verdade;
esta pergunta se o teste prova o que diz provar.

---

## 1. Todo teste de proteção tem o par negativo?

A regra da casa: para todo mecanismo de proteção, dois testes — o que prova que
funciona, e **o que prova que falha quando deveria falhar**. O segundo é o que
vale.

Percorra os mecanismos e confirme que o negativo existe:

| Mecanismo | O negativo que tem de existir |
|---|---|
| escopo de unidade (`RN-A01`, `CA-06`) | ator **pedindo** unidade que não é dele, e recebendo vazio |
| catálogo por ator (ADR-0003, `CS-02`) | persona sem a permissão **não vê** o id no catálogo |
| autorização por registro (ADR-0004) | requisição **forjada** direto ao endpoint, recusada no servidor |
| negativa que não vaza (ADR-0014, `CS-03`) | inexistente e fora-de-escopo com resposta **idêntica** |
| enum fechado (risco R-5) | valor fora do enum levanta `ValidationError` |
| custo restrito (`CA-05`) | custo **ausente** do viewmodel, inclusive para quem tem `custo.ler` |
| imutabilidade (`RN-M02`, `RN-D02`) | `UPDATE`/`DELETE` recusado **pelo banco** |
| CSRF, rate limit | requisição sem token / acima do limite, recusada |

Falta um negativo? Achado. Uma regra que nunca falhou não é evidência de nada.

## 2. Todo critério de aceite tem teste?

Para cada `- [x]` nos arquivos `docs/tasks/T-0NN-*.md`, encontre o teste. Nome
do arquivo, nome da função. Se você não achar em dois minutos, **o AC está
marcado sem lastro** — é o mesmo defeito que a A-002 encontrou.

O caminho inverso também vale: teste que não corresponde a nenhum AC é ou
cobertura extra bem-vinda, ou sinal de que a tarefa não descreveu o que importa.

## 3. Testes que pulam ou não rodam

```bash
cd api && uv run pytest -q -rs        # skips, com a razão
cd api && uv run pytest --collect-only -q | tail -3
cd web && npx vitest run              # há `.skip`, `.todo`, `.only`?
grep -rn "\.skip\|\.only\|xfail\|@pytest.mark.skip" api/tests web/src/testes
```

- **`.only` é bloqueador** — silencia a suíte inteira em volta.
- Teste que pula por falta de infraestrutura (Postgres) é teste que não existe
  quando a infraestrutura não está lá. No CI, isso tem de ser erro, não skip.

## 4. Fakes que divergiram do real

**O risco mais perigoso da suíte hoje.** `api/tests/registry/fakes.py`
reimplementa a interseção de escopo que a porta de dados promete. Se o adaptador
SQLAlchemy real parar de intersectar, **todos os testes de registry continuam
verdes**.

Confira:

- existe teste que roda a **mesma** bateria contra o fake **e** contra o
  repositório real? (contract test) Se não existe, é achado aberto — está
  registrado, e a correção é a T-042.
- o fake implementa alguma regra de negócio que deveria vir do domínio? Fake que
  calcula é fake que pode calcular diferente.
- o fixture tem os casos difíceis, ou só os fáceis? Custo **presente** no
  fixture, para o teste de custo invisível não passar por acidente; dois lotes
  de mesmo número em unidades diferentes; lote vencido dentro da quarentena.

## 5. Asserções fracas

Procure e questione:

- `assert resultado` / `assert x is not None` — passa com quase tudo
- `assert len(linhas) > 0` sem afirmar **quais** linhas
- comparar só o código do erro quando o vazamento estaria na **mensagem**
- `try/except` dentro do teste engolindo a falha que ele deveria pegar
- teste que afirma o que o próprio fixture montou, sem exercitar a regra

## 6. Acoplamento ao relógio e a outra ordem

```bash
grep -rn "date.today()\|datetime.now()\|Date.now()" api/tests web/src/testes
```

Fixture ancorada em `date.today()` faz o caso de fronteira (validade
**exatamente hoje**) virar outra coisa à meia-noite. Ou congele o tempo, ou
construa as datas relativas a uma âncora fixa e afirme a fronteira explicitamente.

Rode a suíte fora de ordem e veja se ainda passa:

```bash
cd api && uv run pytest -q -p no:randomly 2>/dev/null || true
```

Teste que depende de ordem esconde estado compartilhado.

## 7. Tipos nos testes

```bash
cd api && uv run mypy --strict tests
cd web && npx tsc --noEmit
```

> `make typecheck` roda `mypy --strict src` e **não** `tests` — é o achado A-09.
> Enquanto ele estiver aberto, esta verificação é manual e vale a pena.

## 8. A prova final: quebre de propósito

Para os três testes que você considera mais importantes da suíte, **introduza a
violação** que eles deveriam pegar, rode, e confirme que ficam vermelhos. Depois
desfaça.

É como as regras do `arch:check` foram validadas na v1, e é a única forma
honesta de saber que um teste protege alguma coisa.

---

## O relatório

Curto, em `docs/relatorios/A-0NN-testes.md`, ou como seção do relatório de
auditoria de execução se as duas rodaram juntas:

- números: quantos testes, quantos pulam, quantos ACs sem teste
- **a lista de mecanismos sem teste negativo** ← o coração do relatório
- fakes que divergiram, ou risco de divergirem
- asserções fracas encontradas, com arquivo e linha
- o que você quebrou de propósito, e o que ficou vermelho (ou não ficou)

Achado que exige trabalho vira tarefa no BOARD. **Não conserte durante a
auditoria** — misturar apuração e correção esconde o tamanho do problema.
