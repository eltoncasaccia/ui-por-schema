# A-003 — Prontidão para produção: vender para várias empresas, na AWS

| | |
|---|---|
| **Data** | 2026-09-27 |
| **Produzido por** | auditoria pedida pelo dono, fora do board |
| **Pergunta** | O que falta para este sistema rodar **sem erro** em produção na AWS, vendido a **várias** distribuidoras? |
| **Método** | Evidência lida no código e na configuração, nunca na documentação. Conhecimento de nuvem reaproveitado de [`~/archi/docs/setup/aws-passo-a-passo.md`](../../../archi/docs/setup/aws-passo-a-passo.md), onde a conta `farmacia-prod` já está prevista |
| **Resultado** | **Não está pronto, e a distância não é de acabamento — é de arquitetura.** Um bloqueador absoluto (não existe cliente no modelo de dados), um defeito que abre o sistema por esquecimento (`MODO_DEMO` padrão `true`), e três que quebram assim que houver mais de um contêiner |
| **Recomendação** | Tratar como **ciclo 2**, com o multi-tenant como primeira onda. Não publicar conteúdo de marketing antes do bloco 1 — vender o que ainda não isola cliente é dívida que vence na frente do cliente |

> **Regra dos relatórios:** o que não se sustentou aparece com o mesmo destaque
> do que se sustentou. O que **já está pronto** está no §4, com o mesmo peso dos
> bloqueadores — e é bastante.

---

## 1. O veredito, por bloco

| Bloco | Estado | O que decide |
|---|---|---|
| **Isolamento entre clientes** | 🔴 **não existe** | zero ocorrências de `tenant`; nenhum `empresa_id` em tabela nenhuma |
| **Autenticação** | 🟢 pronto | Argon2, tempo uniforme, CSRF, rate limit por conta e por IP |
| **Modo demonstração** | 🔴 **abre por esquecimento** | `MODO_DEMO` tem padrão `true` |
| **Escala horizontal** | 🔴 quebra | rate limit em memória de processo |
| **Infraestrutura** | 🔴 não existe | nenhum arquivo Terraform; só `docker-compose.yml` |
| **Segredos** | 🔴 em arquivo | 19 variáveis em `.env`, incluindo `SESSAO_SECRET` e chaves de LLM |
| **Backup e restauração** | 🔴 não existe | nenhum procedimento, nenhuma restauração testada |
| **Observabilidade** | 🟡 preparada, desligada | LangFuse integrado; as duas chaves estão **vazias** |
| **Teto de custo de LLM** | 🟡 por ator, não por cliente | 30 composições/ator/5 min; nada por empresa |
| **Suíte de testes** | 🟢 forte | 806 testes, suíte adversarial, e2e, portão contra teste que pula |
| **Imagem e CI** | 🟢 pronto | multi-stage, não-root, healthcheck; CI com lint, tipos, testes e arquitetura |
| **Acessibilidade** | 🟡 sem verificação | `design.test.ts` tem 17 asserções e **nenhuma** de contraste |

---

## 2. Os bloqueadores, em ordem de execução

### B-1 · Não existe cliente no modelo de dados 🔴

`grep -ril tenant api/src web/src` devolve **zero**. As três ocorrências de
"empresa" são prosa em comentário. O que existe é **unidade** — CD Matriz, CD
Refrigerado, Uberlândia — que são unidades *dentro de uma* empresa, não
empresas.

Vender para N distribuidoras exige coluna de cliente em toda tabela, filtro em
toda consulta, e — a parte difícil — o cliente atravessando os **três momentos
de autorização** do [ADR-0004](../adr/0004-autorizacao-em-tres-momentos.md). A
tese do projeto é que só o terceiro momento protege, o que roda em cada `load` e
cada `command` com a identidade real. Se essa barreira não carregar o cliente
junto com o ator, o vazamento entre empresas passa exatamente pelo caminho que o
projeto inteiro existe para proteger.

> **Isto contraria uma decisão registrada, e de propósito.** A orientação até
> aqui era não desdobrar tenancy: era POC, e provar o conceito valia mais. A
> mudança de objetivo — vender para várias empresas — é o que revoga aquela
> decisão. Vale registrar em ADR novo, não emendar o antigo em silêncio.

**Não é tarefa. É onda.** Toca schema, repositórios, motor de permissão,
registry, auditoria, seed e a suíte inteira.

### B-2 · `MODO_DEMO` abre o sistema por esquecimento 🔴

[`config.py:26`](../../api/src/estoque/server/config.py) —
`os.environ.get("MODO_DEMO", "true")`. **Falha aberto.** Um deploy que não
declare a variável publica `/api/auth/demo`, que lista as sete personas com
senha `demo` ([`auth.py:202`](../../api/src/estoque/server/rotas/auth.py)).

Correção pequena e imediata: padrão `false`, e o servidor **recusa subir** com
`MODO_DEMO=true` se não estiver em desenvolvimento. É o mesmo desenho do
[ADR-0027](../adr/0027-ambiente-verificado.md): ambiente que se verifica em vez
de confiar.

### B-3 · O que quebra com mais de uma réplica 🔴

O próprio código já registra a limitação, com honestidade —
[`limite.py`](../../api/src/estoque/auth/limite.py): *"o contador não sobrevive a
reinício do processo nem é compartilhado entre réplicas… num cenário com mais de
uma réplica isso vira um limite por réplica, e a proteção se dilui"*.

Em ECS Fargate com duas tarefas, dois efeitos: a força bruta de senha ganha o
dobro de tentativas, e o **teto de custo de token do assistente** (`CS-06`, 30
composições por ator) vira 60. O segundo é dinheiro saindo.

A alternativa que o comentário aponta — contador no banco — custa uma tabela e
uma migração. Com RDS já de pé, é barato.

### B-4 · Nada de infraestrutura, segredos ou backup 🔴

Nenhum `.tf` no repositório. `.env` com 19 variáveis, entre elas `SESSAO_SECRET`
e as chaves de modelo. Nenhuma cópia de segurança, nenhuma restauração testada.

Isto **não precisa ser inventado**: o Archi já tem o caminho escrito, e a
organização da AWS já reserva a conta `farmacia-prod` (§3 abaixo).

### B-5 · Dois achados de segurança abertos 🟡

| | O que é | Por que importa com cliente real |
|---|---|---|
| [A-42](../tasks/ACHADOS.md) | `titulo` do schema é texto livre **sem teto**, e é onde o modelo obedece à injeção. Está marcado `xfail(strict=True)` | com dado de cliente real, deixa de ser achado de relatório e vira incidente |
| [A-43](../tasks/ACHADOS.md) | escrita composta junto de leitura é aceita por uma checagem que **nunca dispara** | condição morta num caminho de escrita é a pior espécie de código morto |

O [R-003](R-003-seguranca-ciclo-1.md) concluiu que nenhum dos dois bloqueava o
**release da POC**. Bloqueiam o de produção.

---

## 3. O caminho para a AWS — reaproveitado do Archi

[`~/archi/docs/setup/aws-passo-a-passo.md`](../../../archi/docs/setup/aws-passo-a-passo.md)
já resolveu este problema uma vez. O que serve aqui, sem refazer:

**A estrutura de contas já prevê este sistema.** A organização tem a OU Produtos
com `archi-prod`, `archi-dev` e — textualmente — *"`farmacia-prod`, só quando o
Estoque-Farmácia subir"*. Conta-membro não pede cartão e a fatura vem detalhada
por conta, o que dá custo por produto sem trabalho extra.

**O mapa de peças vale igual:** VPC, RDS Postgres (substitui o contêiner `db`),
ECR, ECS Fargate, ALB com o certificado, Secrets Manager (substitui o `.env`),
CloudWatch. Este sistema **não** precisa de S3 nem SES no começo — não há anexo
nem email transacional.

**As cinco armadilhas confirmadas em 2026-09-26** valem aqui sem mudança:

1. "Free tier de 12 meses" não existe mais; *Free plan* encerra a conta em 6 meses.
2. MFA no raiz é obrigatório — sem ele o acesso cai em 30 dias.
3. Chave de acesso eterna saiu de moda: `aws configure sso` para pessoa, **OIDC** para o CI.
4. O ALB/CloudFront corta espera longa — **relevante aqui**: a composição do assistente levou 7,6 s com modelo local, e um modelo lento ou um catálogo maior aproxima do teto.
5. Mac constrói imagem **ARM**, CI do GitHub constrói **Intel**. ARM no Fargate é ~20% mais barato, mas imagem e máquina precisam combinar.

**O custo, pela estimativa do Archi para `sa-east-1`:** US$ 90–160 por mês para
um ambiente, mais **US$ 68 por NAT Gateway**. Dois ambientes (staging e
produção) quase dobram. Multi-cliente muda pouco no começo — o mesmo banco
atende várias empresas com isolamento por linha, e a conta só cresce quando o
volume crescer.

> **O que este relatório não faz:** não estima custo próprio deste sistema, e não
> roda a calculadora da AWS. Os números acima são do Archi, para o Archi. Servem
> de ordem de grandeza, não de orçamento.

---

## 4. O que já está pronto — e é bastante

Não é sistema começando. É sistema com um furo estrutural.

| | Evidência |
|---|---|
| **Autenticação** | Argon2 (`PH.hash`/`PH.verify`), resposta e **tempo uniformes** para usuário inexistente e senha errada, senha de no mínimo 10 caracteres, CSRF por par cookie + cabeçalho |
| **Autorização** | motor de permissão, escopo por unidade, catálogo filtrado por ator — e o conjunto **exato** das sete personas congelado em teste (`CS-02`) |
| **Auditoria** | trilha append-only; toda leitura de dado e toda composição viram evento; custo plantado na tabela não sai pela trilha para quem não tem `custo.ler` |
| **O dado não vai para a IA** | `CS-04` provado byte a byte no prompt, e confirmado com modelo real. É o argumento comercial mais forte, e é o mais bem testado |
| **Testes** | 806 passando, 2 pulos com motivo, 1 `xfail` estrito; suíte adversarial onde cada proteção nova foi **sabotada de propósito** para ver o teste ficar vermelho |
| **E2E** | Playwright em servidores próprios contra `estoque_teste`, nunca contra o banco de desenvolvimento |
| **Imagem** | multi-stage, usuário não-root uid 10001, healthcheck, entrypoint próprio |
| **CI** | lint, tipos, testes e arquitetura nos dois lados, mais o portão *"nenhum teste pulou por falta de banco"* |
| **Banco** | migrações Alembic; papel restrito (`estoque_app`) separado do dono, e só migração e seed usam o dono |
| **Agnosticismo de provedor** | trocar de modelo é configuração. **Isto é requisito de venda**, não enfeite: cliente com política de dado exige modelo dentro da própria casa |

---

## 5. Design system — o que vale trazer do Archi

Este projeto **já tem** o seu: tokens em `web/src/estilo.css`, invariantes em
`design.test.ts`, e a semântica de `--ambar` vs `--laranja` documentada em
[`web/CLAUDE.md`](../../web/CLAUDE.md). A identidade do Archi (cianotipia, o
carimbo do arquiteto) é de **outro produto** e não se copia.

O que se copia é o **método**, e são quatro coisas concretas:

| Do Archi | Aqui | Estado |
|---|---|---|
| *"os tokens já passam o contraste AA, verificado por teste"* | `design.test.ts` tem 17 asserções e **nenhuma** sobre contraste | **falta** — e é o maior buraco visual para vender a empresa que exige acessibilidade |
| Estados obrigatórios por componente: carregando, vazio, erro, somente-leitura | existem na prática, não como invariante testada | falta a asserção |
| `<dialog>` nativo com `showModal()`, foco preso, Esc fecha, foco volta — **nunca `window.confirm`** | o diálogo de compartilhar é `role="dialog" aria-modal`, montado à mão | conferir foco e Esc |
| O design system como **documento legível** de ~350 linhas | aqui ele é `design/estoque-bertoni-design-system.html`, com **2,4 MB** | ninguém revisa 2,4 MB — vale um README no formato do Archi |

O padrão de tema escuro em três blocos (`:root`, media query com
`:not([data-theme="light"])`, e `[data-theme="dark"]`) já é o mesmo nos dois
projetos.

---

## 6. O que fazer, em ordem

| Onda | O quê | Por quê nesta ordem |
|---|---|---|
| **0** | `MODO_DEMO` padrão `false` + recusa de subida fora de desenvolvimento | uma tarefa pequena que fecha um buraco aberto. Não depende de nada |
| **0** | fechar A-42 (teto no `titulo`) e A-43 (condição morta) | já estão descritos, já têm teste esperando |
| **1** | **multi-tenant**: schema, repositórios, motor de permissão, registry, auditoria, seed, suíte | tudo depois disso muda se isto mudar. Fazer por último é refazer |
| **2** | rate limit e sessão fora da memória do processo | pré-requisito de rodar mais de uma réplica |
| **3** | Terraform, Secrets Manager, migração no deploy, backup **com restauração testada** | o Archi tem o roteiro (T7.1 a T7.11); aqui vira um por um |
| **4** | observabilidade ligada, alarme, teto de custo de LLM **por cliente** | sem isso, o primeiro cliente caro só aparece na fatura |
| **5** | contraste AA verificado por teste, e o design system como documento | é o que a empresa maior pergunta na diligência |
| **6** | **marketing** | o material já está gravado e espera em `docs/marketing/` |

---

## 6b. O que a própria auditoria já consertou

Dois defeitos apareceram ao exercitar o sistema, e foram corrigidos na hora —
são pequenos, e deixá-los para depois seria deixar armadilha montada.

| | O que era | Como está |
|---|---|---|
| [A-51](../tasks/ACHADOS.md) | `LLM_BASE_URL` valia para **todos** os provedores. Trocar para `PROVEDOR=openrouter` com Ollama configurado mandava a chave e o modelo da Anthropic para `localhost:11434`, e o `make modelo` **confirmava o destino errado** | a variável só vale para `compativel`; `make modelo` pergunta à fábrica em vez de ecoar o ambiente. Teste negativo conferido em vermelho |
| [A-52](../tasks/ACHADOS.md) | a saída por venda deixava enviar com cliente e nota vazios; o servidor recusava com `422 Entrada invalida.`, genérico, **depois** da confirmação | o botão trava e a tela diz o que falta, no mesmo tom do aviso de `RN-L03`. Dois negativos em `web/e2e/saida.spec.ts` |

O A-52 só apareceu porque a primeira versão do teste de saída afirmava algo
fraco — "o lote continua aparecendo na lista" — e passava. Trocada a asserção
pelo **saldo lido de novo**, o teste ficou vermelho e o defeito apareceu.
Registrado aqui porque é a lição, não o defeito: asserção fraca não é teste
meia-boca, é teste que esconde.

**Estado verificado em 2026-09-27:** `make check` verde (982 testes na API, 142
no cliente, 2 pulos com motivo, 1 `xfail`), `make e2e` verde (29 testes, nenhum
pulo).


## 7. O que esta auditoria não fez

- **Não rodou a suíte.** Os 806 testes são o número do
  [R-003](R-003-seguranca-ciclo-1.md), de 2026-09-14. Não reconferi.
- **Não auditou LGPD nem regulatório.** Distribuidora farmacêutica com AFE e
  Portaria 344/98 tem exigências de retenção e de rastreabilidade que este
  relatório não tocou, e que mudam o desenho de backup.
- **Não estimou custo deste sistema.** Os números do §3 são do Archi.
- **Não mediu desempenho sob carga.** Nenhuma ideia de quantos usuários
  simultâneos o desenho atual aguenta.
- **Não avaliou o modelo comercial.** Uma instância por cliente é a alternativa
  ao multi-tenant, e é mais simples e mais cara. A escolha é do dono, e é a
  primeira pergunta da onda 1.
