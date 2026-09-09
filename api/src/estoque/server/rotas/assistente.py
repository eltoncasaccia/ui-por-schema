"""`/api/assistente/compor`: modelo -> schema -> VALIDA contra o catalogo do ator.

A saida do modelo e' PAYLOAD NAO-CONFIAVEL. `validar_schema` roda aqui, e o
que sai daqui autoriza RENDERIZAR, nunca escrever (ADR-0002).
"""

from typing import Any

from fastapi import APIRouter, Cookie
from pydantic import BaseModel

from estoque.application.registry.registry import catalogo_de
from estoque.application.schema.validar import validar_schema
from estoque.assistant.adapter import AdaptadorModelo, ErroDeModelo, extrair_json
from estoque.assistant.fabrica import criar_adaptador
from estoque.auditoria import registro as aud
from estoque.domain.erros import ErroDominio
from estoque.server.deps import CFG, OBS, ator_ou_falhar, motor, ok, tamanho

rotas = APIRouter()


class Pergunta(BaseModel):
    pergunta: str
    modo: str = CFG.modo_decodificacao


def _adaptador() -> AdaptadorModelo:
    """Escolhido por configuracao (PROVEDOR), nao por codigo."""
    return criar_adaptador(modelo=CFG.modelo)


@rotas.post("/api/assistente/compor")
async def compor(corpo: Pergunta, sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    async with motor.begin() as c:
        ator = await ator_ou_falhar(c, sessao)
        cat = catalogo_de(ator)
        if not cat:
            # ADR-0019: recem-cadastrado sem papel nao tem vocabulario.
            raise ErroDominio("nao_autorizado", "Seu usuario ainda nao tem papel atribuido.")

        try:
            adaptador = _adaptador()
        except ErroDeModelo as e:
            raise ErroDominio("invalido", str(e)) from e

        modo = "restrito" if corpo.modo == "restrito" else "livre"
        r = await adaptador.compor(corpo.pergunta, cat, modo=modo)  # type: ignore[arg-type]
        if r.trace.erro:
            raise ErroDominio("invalido", "O assistente nao respondeu. Tente de novo.")

        try:
            bruto = extrair_json(r.bruto)
        except ValueError:
            r.trace.erro = "resposta sem JSON"
            bruto = None

        resultado = validar_schema(bruto, ator) if bruto is not None else None
        r.trace.aceitos = resultado.aceitos if resultado else []
        r.trace.rejeitados = (
            [(x.tipo, x.motivo) for x in resultado.rejeitados] if resultado else []
        )

        # Telemetria externa. Nunca levanta — e a auditoria abaixo, que e'
        # requisito regulatorio, nao depende dela.
        OBS.composicao(trace=r.trace, ator_id=ator.id, papel=ator.papel, catalogo=len(cat))

        # RN-D05 / CS-05: a resposta do assistente e' auditada, com o que foi
        # aceito E o que foi rejeitado.
        await aud.registrar(
            c,
            ator_id=ator.id,
            acao="compor",
            origem="assistente",
            valor_novo={"pergunta": corpo.pergunta, **r.trace.resumo()},
        )

    schema = resultado.schema if resultado else None
    return ok(
        {
            "schema": schema.model_dump() if schema else None,
            "blocos": [
                {"tipo": b.tipo, "params": b.params, "tamanho": tamanho(b.tipo)}
                for b in (schema.blocos if schema else ())
            ],
        },
        trace=r.trace.resumo(),
    )
