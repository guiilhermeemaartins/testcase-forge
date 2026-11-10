import pytest
from pydantic import ValidationError

from forge.schema import CasoDeTeste, Passo, SuiteDeTestes


def caso(**over):
    base = dict(
        id="CT-001",
        titulo="Enviar solicitacao com dados validos",
        tipo="sucesso",
        prioridade="alta",
        regra_coberta="regra A",
        pre_condicoes=[],
        passos=[Passo(acao="Clique em Enviar")],
        resultado_esperado="A tela exibe o protocolo 2026-000001",
    )
    base.update(over)
    return base


def test_caso_valido():
    c = CasoDeTeste(**caso())
    assert c.id == "CT-001"


@pytest.mark.parametrize("ruim", ["CT-1", "ct-001", "CT001", "X-001", "CT-0001"])
def test_id_fora_do_padrao_e_rejeitado(ruim):
    with pytest.raises(ValidationError):
        CasoDeTeste(**caso(id=ruim))


def test_tipo_desconhecido_e_rejeitado():
    with pytest.raises(ValidationError):
        CasoDeTeste(**caso(tipo="regressao"))


def test_caso_sem_passo_e_rejeitado():
    with pytest.raises(ValidationError):
        CasoDeTeste(**caso(passos=[]))


def test_resultado_esperado_curto_e_rejeitado():
    with pytest.raises(ValidationError):
        CasoDeTeste(**caso(resultado_esperado="ok"))


def test_suite_precisa_de_regra_e_caso():
    with pytest.raises(ValidationError):
        SuiteDeTestes(requisito="x", regras_identificadas=[], casos=[CasoDeTeste(**caso())])
    with pytest.raises(ValidationError):
        SuiteDeTestes(requisito="x", regras_identificadas=["regra A"], casos=[])
