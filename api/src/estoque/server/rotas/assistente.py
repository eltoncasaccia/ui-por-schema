"""`/api/assistente/compor`: modelo -> schema -> VALIDA contra o catalogo do ator.

A saida do modelo e' PAYLOAD NAO-CONFIAVEL. `validar_schema` roda aqui, e o
que sai daqui autoriza RENDERIZAR, nunca escrever (ADR-0002).

**Rate limit por ator (`CS-06`, T-011 AC-6).** Nao existia: a T-040 entregou
rate limit no LOGIN e o rotulou `CS-06`, mas sao protecoes diferentes — forca
bruta de senha e' uma, custo de token por ator e' outra (achado A-34). Cada
composicao chama o modelo e custa dinheiro de verdade; sem teto por ator, um
laco no cliente esvazia o orcamento (ADR-0011). O teto e' conferido ANTES de
falar com o modelo, senao ele nao protege do que existe para proteger.
"""

from typing import Any

from fastapi import APIRouter, Cookie, Request
from pydantic import BaseModel

from estoque.application.registry.registry import catalogo_de
from estoque.application.schema.validar import validar_schema
from estoque.assistant.adapter import AdaptadorModelo, ErroDeModelo, extrair_json
from estoque.assistant.fabrica import criar_adaptador
from estoque.auditoria import registro as aud
from estoque.auth.limite import Limitador
from estoque.domain.erros import ErroDominio
from estoque.server.deps import CFG, OBS, ator_ou_falhar, bloco_resposta, motor, ok

rotas = APIRouter()

# Uma pessoa faz um punhado de perguntas por minuto; 30 em 5 min e' folgado para
# gente e aperta o laco automatico, que e' o caso caro. O teto por IP e' mais
# alto porque um CD inteiro sai por um NAT so' — limitar IP como se fosse pessoa
# derrubaria o turno inteiro por causa de um cliente com defeito.
COMPOSICOES_POR_ATOR = 30
COMPOSICOES_POR_IP = 120
JANELA_COMPOR_S = 300.0

# Reusa o `Limitador` de `auth/`: janela deslizante ja' testada (T-040). La' o
# metodo se chama `registrar_falha` porque no login **so' a falha** conta; aqui
# o evento e' a CHAMADA — toda composicao gasta cota, inclusive a que deu certo,
# porque o custo e' do token e nao do erro. Renomear o metodo mexeria em arquivo
# da T-040, entao fica o nome de la' e a razao aqui.
LIMITE = Limitador(
    tentativas_conta=COMPOSICOES_POR_ATOR,
    tentativas_ip=COMPOSICOES_POR_IP,
    janela_s=JANELA_COMPOR_S,
)


class Pergunta(BaseModel):
    pergunta: str
    modo: str = CFG.modo_decodificacao


def _adaptador() -> AdaptadorModelo:
    """Escolhido por configuracao (PROVEDOR), nao por codigo."""
    return criar_adaptador(modelo=CFG.modelo)


@rotas.post("/api/assistente/compor")
async def compor(
    corpo: Pergunta, req: Request, sessao: str | None = Cookie(default=None)
) -> dict[str, Any]:
    async with motor.connect() as conexao:
        ator = await ator_ou_falhar(conexao, sessao)

    # CS-06 · T-011 AC-6. Antes do modelo, e antes de abrir a transacao: a
    # auditoria da recusa precisa SOBREVIVER ao `raise`, e um `raise` dentro do
    # `motor.begin()` reverteria o proprio registro (mesmo desenho do login).
    ip = req.client.host if req.client else "desconhecido"
    if LIMITE.bloqueado(conta=ator.id, ip=ip):
        async with motor.begin() as c_lim:
            await aud.registrar(
                c_lim,
                ator_id=ator.id,
                acao="assistente_bloqueado",
                origem="assistente",
                valor_novo={"motivo": "limite", "ip": ip},
            )
        raise ErroDominio("limite", "Muitas perguntas em pouco tempo. Aguarde um instante.")
    LIMITE.registrar_falha(conta=ator.id, ip=ip)

    async with motor.begin() as c:
        cat = catalogo_de(ator)
        if not cat:
            # ADR-0019: recem-cadastrado sem papel nao tem vocabulario.
            raise ErroDominio("nao_autorizado", "Seu usuario ainda nao tem papel atribuido.")

        try:
            adaptador = _adaptador()
        except ErroDeModelo as e:
            raise ErroDominio("invalido", str(e)) from e

        modo = "restrito" if corpo.modo == "restrito" else "livre"
        # T-043: a observacao ENVOLVE o trabalho, entao a duracao de cada span e'
        # a real. Telemetria nunca levanta — e a auditoria abaixo, que e'
        # requisito regulatorio, nao depende dela.
        with OBS.ao_vivo(pergunta=corpo.pergunta, ator_id=ator.id, papel=ator.papel) as obs:
            with obs.etapa("gerar-composicao") as etapa:
                r = await adaptador.compor(corpo.pergunta, cat, modo=modo)  # type: ignore[arg-type]
                etapa.detalhar(trace=r.trace)
            if r.trace.erro:
                obs.concluir(trace=r.trace, catalogo=len(cat))
                raise ErroDominio("invalido", "O assistente nao respondeu. Tente de novo.")

            with obs.etapa("validar-schema") as etapa:
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
                etapa.detalhar(trace=r.trace)

            obs.concluir(trace=r.trace, catalogo=len(cat))

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
            "blocos": [bloco_resposta(b) for b in (schema.blocos if schema else ())],
        },
        trace=r.trace.resumo(),
    )
