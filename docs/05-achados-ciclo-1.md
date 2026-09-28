# Achados do ciclo 1

Contraparte de [`00-achados-v1.md`](./00-achados-v1.md), agora para o ciclo que
levou a POC a ter escrita, permissão de verdade e medição com modelo real. A
mesma regra vale: o que não se sustentou aparece com o mesmo destaque do que
se sustentou.

Isto é a narrativa. Os números e o checklist de release estão em
[R-004](./relatorios/R-004-fechamento-ciclo-1.md); o registro achado-a-achado,
em [`docs/tasks/ACHADOS.md`](./tasks/ACHADOS.md) (o que ainda exige ação) e
[`docs/relatorios/achados-resolvidos.md`](./relatorios/achados-resolvidos.md)
(os 31 já fechados, com o teste que prova).

---

## O que este ciclo existia para responder

A v1 provou a arquitetura de composição, mas era 100% leitura, sem
autenticação, e nunca rodou com uma API key real — todos os números vieram de
um parser simulado. Três perguntas ficaram abertas: **escrita é viável sem o
modelo autorizar nada? permissão real, em três momentos, se sustenta sob
sabotagem deliberada? e com que frequência um modelo real — não um mock —
emite schema válido?**

As três têm resposta agora.

---

## O que se sustentou

- **A separação entre plano de render e plano de escrita não quebrou uma
  única vez.** 57 tarefas, 24 componentes registrados, 6 tipos de comando de
  escrita, e o contrato de import-linter *"assistente nunca alcança comandos
  de escrita"* continua `KEPT` desde que foi escrito. Não é convenção — é
  fronteira de processo, verificada em CI a cada `make check`.
- **Autorização em três momentos resiste a sabotagem deliberada.** Toda
  proteção que a T-033 testou foi sabotada de propósito (comentar a
  checagem, remover o filtro) e o teste correspondente ficou vermelho — é a
  prova de que o teste prova algo, não só que existe. CS-01 a CS-06 passam
  os seis, incluindo CS-04 (injeção de prompt via dado), o requisito que o
  PRD chamava de "menor confiança do release" — passou byte a byte, com
  modelo real.
- **O modelo real emite schema válido com frequência alta o bastante para
  confiar.** 83,7%–95,3% conforme o modelo, medido em 43 perguntas reais,
  dois modelos, dois modos — nunca o adaptador mock, que foi o erro central
  da v1. `haiku-4.5` bate a meta de 95% do PRD; nenhuma das 15 sondas
  negativas vazou dado ou compôs escrita, nas quatro combinações.
- **O mesmo componente serve rota e composição do assistente, provado byte a
  byte.** `/vencimento` e uma composição equivalente do assistente produzem
  o **mesmo HTML** — não "parecido", idêntico, comparado string a string em
  teste. É o ADR-0005 em forma de asserção, não de intenção.
- **Teste negativo pegou bug real que teste positivo nunca pegaria.** A
  lista é longa o bastante para valer a pena contar: A-49 (escrita por rota
  nunca chegava ao servidor — só apareceu simulando um clique de verdade,
  não com mock), A-53 (leitor de código de barras nunca lia nada — só
  apareceu no navegador, os 12 testes com mock passavam), A-44 (testes
  gravando no banco de desenvolvimento, 262 usuários fantasma), A-27 (`make
  modelo` confirmava o destino errado da chave de API).
- **Paralelismo com propriedade exclusiva de arquivo funcionou para
  código.** Múltiplas sessões, múltiplas tarefas, e os dois arquivos gerados
  (`registry/indice.py`, `views/indice.ts`) absorveram o que seria 44
  conflitos de merge garantidos.

---

## O que custou, e que ninguém menciona no resumo de uma linha

- **~US\$ 2,65 de gasto real de API só para fechar T-032** — a suíte de
  avaliação foi executada quatro vezes (dois modelos, dois modos) contra o
  catálogo de 24 componentes. Um erro de caminho (a linha de base tentando
  gravar em `/docs`, um diretório que só existe no host, não no container)
  desperdiçou uma execução inteira de `sonnet-5` (~US\$ 0,58) — teve que
  rodar de novo depois do fix.
- **Recriar a imagem Docker da API duas vezes** porque o serviço não tem bind
  mount para o host — mudança de código em `api/src/` não aparece dentro do
  container até `docker compose build`. Custou tempo, não dinheiro, mas é o
  tipo de armadilha que o `CLAUDE.md` já documenta para `make migrate`
  (perde o mapeamento de porta) e que se repetiu, de outro jeito, aqui.
- **`docker compose run` sem o override local recriou o banco sem a porta
  publicada** — a mesma classe de armadilha do `make migrate`, disparada por
  um comando diferente. `make check-api` quebrou inteiro com erro de conexão
  até alguém notar que a causa não era código.
- **Uma branch com evidência necessária quase foi apagada por engano.**
  `tarefa/T-017` guardava a única prova de data de um commit que uma tarefa
  aberta (T-056) ainda precisava — apagada numa limpeza de repositório antes
  de checar se alguma tarefa dependia dela. Restaurada a tempo porque a
  cópia local ainda existia; o processo que devia ter pego isso antes
  (checar achados e tarefas abertas antes de apagar uma branch) não pegou.
- **43 casos de avaliação escritos de uma vez, sem piloto.** Pelo menos 5
  tinham composição esperada questionável — só apareceu depois da execução
  real, que já tinha custo. Um piloto pequeno teria pego o padrão antes de
  escalar.

---

## O que foi cortado ou ficou sem número, e por quê

- **Suíte de avaliação em CI** — nunca teve tarefa própria. `make eval`
  existe e funciona, mas nada dispara automaticamente a cada mudança de
  catálogo ou prompt, como o PRD §11 pedia. É o único item vermelho do
  checklist de release — ver [R-004 §1](./relatorios/R-004-fechamento-ciclo-1.md#1-checklist-de-release-do-prd-11).
- **RNF-06 (temperatura retida 5 anos)** — verificado por ausência de job de
  expurgo, não por medição com volume real de 5 anos. Gerar esse volume só
  para este relatório não teria valor de produto.
- **CA-06 (escopo de unidade)** continua parcial — provado na fila de
  vencimento e em quatro componentes de lote, não no catálogo inteiro.
- **Inventário e transferência (`RN-I`, `RN-T`) inteiros fora do ciclo** —
  decisão do [ADR-0010](./adr/0010-corte-de-escopo-ciclo-1.md), confirmada
  contra os oito critérios de aceite do cliente: nenhum depende do que saiu.
- **Série histórica no LangFuse** — nunca ligada. Telemetria com `401` nas
  tentativas (A-10), sem dono até hoje.

---

## Veredito

O ciclo 1 responde as três perguntas que existia para responder, com número,
não com intuição — e o número, nos três casos, é bom o bastante para seguir.
O que não se sustentou está nomeado, tem dono ou está marcado como sem dono
de propósito, e nenhum item do que ficou vermelho é sobre a tese central: é
sobre processo de CI, sobre um documento desatualizado, e sobre casos de
teste que precisam de revisão. A tese — modelo compõe, nunca escreve,
autorização em três momentos — está de pé, e está de pé porque foi testada
tentando derrubá-la, não porque ninguém tentou.

Detalhe completo, número a número: [R-004](./relatorios/R-004-fechamento-ciclo-1.md).
