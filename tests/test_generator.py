"""O gerador e testado com provider mockado: nada de rede nos testes."""

import json
import pathlib

import pytest

from forge.auditor import auditar
from forge.generator import gerar_suite
from forge.provider import MockProvider

MOCK = (pathlib.Path(__file__).parent.parent / "exemplos" / "resposta-mock.json").read_text(
    encoding="utf-8"
)


def test_gera_suite_valida_a_partir_da_resposta_do_modelo():
    suite = gerar_suite("requisito qualquer", MockProvider(MOCK))
    assert len(suite.casos) == 6
    assert len(suite.regras_identificadas) == 6


def test_suite_do_mock_passa_na_auditoria():
    rel = auditar(gerar_suite("requisito qualquer", MockProvider(MOCK)))
    assert rel.aprovado, rel.texto()


def test_aceita_resposta_com_cerca_de_codigo():
    suite = gerar_suite("req", MockProvider("```json\n" + MOCK + "\n```"))
    assert len(suite.casos) == 6


def test_aceita_resposta_com_texto_em_volta():
    suite = gerar_suite("req", MockProvider("Aqui estao os casos:\n" + MOCK + "\nEspero ter ajudado!"))
    assert len(suite.casos) == 6


def test_tenta_de_novo_quando_o_modelo_erra_o_formato():
    """Primeira resposta invalida, segunda valida: o gerador reenvia o erro."""

    class ProviderInstavel:
        def __init__(self):
            self.n = 0

        def gerar(self, prompt):
            self.n += 1
            if self.n == 1:
                # id fora do padrao: o schema rejeita
                ruim = json.loads(MOCK)
                ruim["casos"][0]["id"] = "CT-1"
                return json.dumps(ruim)
            return MOCK

    p = ProviderInstavel()
    suite = gerar_suite("req", p)
    assert p.n == 2
    assert len(suite.casos) == 6


def test_falha_explicita_quando_o_modelo_nunca_acerta():
    with pytest.raises(ValueError, match="nao produziu uma suite valida"):
        gerar_suite("req", MockProvider("isso nao e json"))
