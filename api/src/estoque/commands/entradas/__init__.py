"""Schemas de entrada dos comandos — um modulo por tarefa de escrita.

**Pacote, e nao um arquivo so', por causa da propriedade exclusiva.** Cinco
tarefas de W4 registram comando; se todas declarassem seus schemas no mesmo
arquivo, seria o problema que `make gerar-indice` existe para resolver, agora em
outro lugar (acordo de trabalho §4, achado A-15).

Este `__init__` fica VAZIO de proposito. Quem importa um schema importa o modulo
dele — `commands.entradas.lote` — e nao arrasta os schemas das outras tarefas
junto. Re-exportar aqui devolveria o arquivo compartilhado pela porta dos fundos.

**A regra que vale para todo modulo deste pacote:** so' pydantic e `domain`. O
`registry` importa daqui para declarar o `CommandDef`, e o contrato 2 do
import-linter proibe `registry -> sqlalchemy`, inclusive por caminho indireto.
Um import de `pipeline`, de `data` ou de SQLAlchemy num modulo daqui quebra o
contrato na hora — e ha' teste percorrendo o grafo, em
`tests/registry/test_quarentena_liberar.py`.
"""
