"""Regras extras: quem usa a ferramenta acrescenta as suas, sem mexer no auditor."""

import pathlib

import pytest

from forge.auditor import Achado, auditar, carregar_regras
from forge.cli import main
from forge.schema import CasoDeTeste, Passo, SuiteDeTestes

RAIZ = pathlib.Path(__file__).parent.parent
REGRA_DE_EXEMPLO = RAIZ / "exemplos" / "regra_extra.py"
SAIDA_REAL_LOGIN = RAIZ / "exemplos" / "saidas-reais" / "02-login-por-perfil.yaml"


def suite_valida(dado=None):
    def caso(id_, tipo):
        return CasoDeTeste(
            id=id_,
            titulo=f"Caso {id_}",
            tipo=tipo,
            prioridade="alta",
            regra_coberta="regra A",
            pre_condicoes=[],
            passos=[Passo(acao="Clique em Enviar", dado=dado)],
            resultado_esperado="A tela exibe a mensagem 'Protocolo gerado'",
        )

    return SuiteDeTestes(
        requisito="r",
        regras_identificadas=["regra A"],
        casos=[caso("CT-001", "sucesso"), caso("CT-002", "falha")],
    )


def test_sem_regra_extra_o_resultado_nao_muda():
    assert auditar(suite_valida()).achados == []
    assert auditar(suite_valida(), regras_extras=[]).achados == []


def test_regra_extra_que_bloqueia_reprova_a_suite():
    def regra_sempre_bloqueia(suite):
        return [Achado("bloqueio", "minha_regra", "motivo")]

    rel = auditar(suite_valida(), regras_extras=[regra_sempre_bloqueia])
    assert not rel.aprovado
    assert any(a.regra == "minha_regra" for a in rel.bloqueios)


def test_regra_extra_de_aviso_nao_reprova():
    def regra_so_avisa(suite):
        return [Achado("aviso", "minha_regra", "motivo")]

    rel = auditar(suite_valida(), regras_extras=[regra_so_avisa])
    assert rel.aprovado
    assert len(rel.avisos) == 1


def test_regra_extra_que_devolve_lixo_falha_de_forma_explicita():
    def regra_errada(suite):
        return ["isto nao e um Achado"]

    with pytest.raises(ValueError, match="regra_errada"):
        auditar(suite_valida(), regras_extras=[regra_errada])


def test_carrega_so_funcoes_que_comecam_com_regra(tmp_path):
    arquivo = tmp_path / "minhas.py"
    arquivo.write_text(
        "from forge.auditor import Achado\n"
        "def auxiliar(suite):\n"
        "    return []\n"
        "def regra_b(suite):\n"
        "    return [Achado('aviso', 'b', 'x')]\n"
        "def regra_a(suite):\n"
        "    return []\n",
        encoding="utf-8",
    )
    regras = carregar_regras(str(arquivo))
    assert [r.__name__ for r in regras] == ["regra_a", "regra_b"]


def test_arquivo_sem_nenhuma_regra_e_erro(tmp_path):
    arquivo = tmp_path / "vazio.py"
    arquivo.write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="regra_"):
        carregar_regras(str(arquivo))


def test_arquivo_inexistente_e_erro(tmp_path):
    with pytest.raises(ValueError, match="nao encontrado"):
        carregar_regras(str(tmp_path / "nao_existe.py"))


def test_regra_de_exemplo_avisa_dado_preenchido_com_marcador():
    regras = carregar_regras(str(REGRA_DE_EXEMPLO))
    rel = auditar(suite_valida(dado="Nenhum"), regras_extras=regras)
    assert rel.aprovado
    assert [a.regra for a in rel.avisos] == ["dado_sem_marcador", "dado_sem_marcador"]


def test_regra_de_exemplo_aceita_dado_real_e_dado_omitido():
    regras = carregar_regras(str(REGRA_DE_EXEMPLO))
    assert auditar(suite_valida(dado="usuario@dominio.com"), regras_extras=regras).achados == []
    assert auditar(suite_valida(dado=None), regras_extras=regras).achados == []


def test_cli_audita_saida_real_com_a_regra_de_exemplo(capsys):
    codigo = main(["auditar", str(SAIDA_REAL_LOGIN), "--regras", str(REGRA_DE_EXEMPLO)])
    saida = capsys.readouterr().out
    assert codigo == 0  # aviso nao reprova
    assert "APROVADO com avisos" in saida
    assert saida.count("dado_sem_marcador") == 8


def test_cli_com_arquivo_de_regras_inexistente_sai_com_2(capsys):
    codigo = main(["auditar", str(SAIDA_REAL_LOGIN), "--regras", "nao_existe.py"])
    assert codigo == 2
    assert "nao encontrado" in capsys.readouterr().err
