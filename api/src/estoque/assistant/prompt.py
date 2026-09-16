"""Montagem do prompt. ADR-0012.

REGRA DESTE MODULO, verificada por import-linter:

    Nenhum dado de banco entra no prompt.

O modelo recebe: a pergunta do usuario, o catalogo (texto escrito por nos) e os
enums. NAO recebe linhas de dados. Isso fecha o vetor de injecao de prompt via
conteudo do banco por CONSTRUCAO, e nao por heuristica — nao existe sanitizacao
confiavel de linguagem natural.

E' possivel porque o modelo escolhe QUAL PERGUNTA FAZER, nao qual resposta dar.
Os dados sao carregados DEPOIS da composicao, pelo `load` autorizado, e vao
direto para a tela.

Custo aceito: o assistente nao consegue resumir nem interpretar o conteudo dos
dados. Ele responde COM TELAS, nao com frases sobre os dados.
"""

import json
from collections.abc import Mapping, Sequence
from typing import Any

INSTRUCAO = """\
Voce compoe telas de um sistema de controle de estoque farmaceutico escolhendo
componentes de um catalogo. Voce NAO escreve codigo, NAO inventa dados e NAO
inventa nomes de componentes.

Responda SOMENTE com JSON neste formato, sem texto antes ou depois:

{"versao": 1, "titulo": "<curto>", "blocos": [{"tipo": "<id>", "params": {...}}]}

Regras:
- `tipo` deve ser um id EXATO do catalogo abaixo. Nao invente ids.
- `params` so' aceita os campos listados; para campos com `valores`, use um dos
  valores exatos. Nao invente valores.
- Nao inclua numeros, nomes ou dados na resposta: os componentes buscam os
  proprios dados.
- Se a pergunta nao puder ser respondida com o catalogo, devolva
  {"versao": 1, "blocos": []}.
- Prefira poucos blocos. Um bloco costuma bastar.
- Se a pergunta for VAGA e couber em mais de um componente (ex.: "quero
  registrar", "quero ver"), NAO escolha por conta propria: devolva
  {"versao": 1, "blocos": [], "esclarecer": ["<id>", "<id>"]} com ate 4 ids do
  catalogo, para a pessoa escolher. Fora desse caso, `esclarecer` e' [].
"""


def montar(pergunta: str, catalogo: Sequence[Mapping[str, Any]]) -> str:
    """Constroi o prompt. `catalogo` ja' vem filtrado pelo ator (ADR-0003).

    A pergunta do usuario e' entrada nao confiavel e e' delimitada. O pior caso
    de uma pergunta hostil e' compor algo inutil DENTRO do proprio catalogo do
    ator — nunca acessar o que ele nao pode (ADR-0003, ADR-0004).
    """
    linhas = [INSTRUCAO, "\n## Catalogo disponivel\n"]
    for c in catalogo:
        linhas.append(f"### {c['id']}")
        linhas.append(c["description"])
        linhas.append(f"params: {json.dumps(c['params'], ensure_ascii=False)}")
        linhas.append(f"exemplos: {'; '.join(c['examples'])}\n")
    linhas.append("\n## Pergunta do usuario\n")
    linhas.append("<pergunta>")
    linhas.append(pergunta.strip())
    linhas.append("</pergunta>")
    return "\n".join(linhas)
