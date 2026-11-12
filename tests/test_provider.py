"""Erros de rede do provider. Nenhum teste chama a API: a rede e substituida."""

import pathlib

import pytest

from forge.cli import main
from forge.provider import ErroDoProvider, GeminiProvider

EXEMPLO = pathlib.Path(__file__).parent.parent / "exemplos" / "01-solicitacao-alvara.md"


def _rede_que_estoura_o_tempo(*args, **kwargs):
    raise TimeoutError("The read operation timed out")


def test_timeout_de_leitura_vira_erro_do_provider(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", _rede_que_estoura_o_tempo)
    provider = GeminiProvider(chave="chave-de-teste", modelo="modelo-de-teste")
    with pytest.raises(ErroDoProvider, match="Tempo esgotado"):
        provider.gerar("prompt")


def test_timeout_sai_com_codigo_2_e_nao_com_o_codigo_de_reprovado(monkeypatch, capsys):
    # 1 significa "a auditoria reprovou a suite". Queda de rede nao pode
    # devolver o mesmo codigo, senao um pipeline confunde as duas coisas.
    monkeypatch.setattr("urllib.request.urlopen", _rede_que_estoura_o_tempo)
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    codigo = main(["gerar", str(EXEMPLO)])
    assert codigo == 2
    assert "Tempo esgotado" in capsys.readouterr().err
