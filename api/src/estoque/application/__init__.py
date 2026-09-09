"""Camada de aplicacao — os casos de uso, entre o dominio e os adaptadores.

Arquitetura hexagonal (ADR-0031). Esta camada orquestra o dominio falando SO'
com portas (`data/porta.py`, `assistant/adapter.py`), e nunca com a
implementacao delas.

    registry/   casos de uso de LEITURA  — o catalogo, `load` e `select`
    commands/   casos de uso de ESCRITA  — o pipeline e os comandos
    schema/     validacao da entrada nao-confiavel, antes de tudo

Os tres estavam soltos na raiz do pacote e pareciam tres naturezas diferentes.
Sao a mesma: caso de uso. O que muda entre eles e' a direcao — ler, escrever,
ou recusar entrada.

**A separacao entre `registry/` e `commands/` nao e' arrumacao**: e' a condicao
para o contrato 3 do import-linter existir, e com ele o ADR-0002. Ver o
`__init__` de `commands/` e o ADR-0030.
"""
