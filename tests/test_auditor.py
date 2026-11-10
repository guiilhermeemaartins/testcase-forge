"""Os testes do auditor nao chamam a API: as regras sao deterministicas."""

from forge.auditor import auditar
from forge.schema import CasoDeTeste, Passo, SuiteDeTestes


def c(id_, tipo, regra, resultado="A tela exibe a mensagem 'Protocolo gerado'", titulo=None):
    return CasoDeTeste(
        id=id_,
        titulo=titulo or f"Caso {id_}",
        tipo=tipo,
        prioridade="alta",
        regra_coberta=regra,
        pre_condicoes=[],
        passos=[Passo(acao="Clique em Enviar")],
        resultado_esperado=resultado,
    )


def suite(regras, casos):
    return SuiteDeTestes(requisito="r", regras_identificadas=regras, casos=casos)


def test_suite_completa_e_aprovada():
    rel = auditar(suite(["regra A"], [c("CT-001", "sucesso", "regra A"), c("CT-002", "falha", "regra A")]))
    assert rel.aprovado, rel.texto()
    assert rel.avisos == []


def test_regra_sem_caso_reprova():
    rel = auditar(
        suite(["regra A", "regra B"], [c("CT-001", "sucesso", "regra A"), c("CT-002", "falha", "regra A")])
    )
    assert not rel.aprovado
    assert any(a.regra == "cobertura" and "regra B" in a.mensagem for a in rel.bloqueios)


def test_caso_apontando_regra_inexistente_reprova():
    rel = auditar(suite(["regra A"], [c("CT-001", "sucesso", "regra A"), c("CT-002", "falha", "regra Z")]))
    assert not rel.aprovado
    assert any(a.regra == "rastreabilidade" for a in rel.bloqueios)


def test_suite_sem_caso_de_falha_reprova():
    rel = auditar(suite(["regra A"], [c("CT-001", "sucesso", "regra A")]))
    assert not rel.aprovado
    assert any(a.regra == "caminho_negativo" for a in rel.bloqueios)


def test_resultado_vago_reprova():
    rel = auditar(
        suite(
            ["regra A"],
            [
                c("CT-001", "sucesso", "regra A", resultado="O sistema funciona corretamente"),
                c("CT-002", "falha", "regra A"),
            ],
        )
    )
    assert not rel.aprovado
    assert any(a.regra == "resultado_verificavel" for a in rel.bloqueios)


def test_resultado_vago_pega_acento_e_caixa():
    rel = auditar(
        suite(
            ["regra A"],
            [
                c("CT-001", "sucesso", "regra A", resultado="A acao ocorre CONFORME ESPERADO na tela"),
                c("CT-002", "falha", "regra A"),
            ],
        )
    )
    assert not rel.aprovado


def test_termo_vago_dentro_de_outra_palavra_nao_reprova():
    # "incorretamente" contem "corretamente", mas e um resultado verificavel:
    # diz exatamente qual mensagem aparece.
    rel = auditar(
        suite(
            ["regra A"],
            [
                c("CT-001", "sucesso", "regra A"),
                c(
                    "CT-002",
                    "falha",
                    "regra A",
                    resultado="A tela exibe a mensagem 'Senha informada incorretamente'",
                ),
            ],
        )
    )
    assert rel.aprovado, rel.texto()


def test_id_repetido_reprova():
    rel = auditar(suite(["regra A"], [c("CT-001", "sucesso", "regra A"), c("CT-001", "falha", "regra A")]))
    assert not rel.aprovado
    assert any(a.regra == "ids_unicos" for a in rel.bloqueios)


def test_id_fora_de_sequencia_e_aviso_nao_bloqueio():
    rel = auditar(suite(["regra A"], [c("CT-001", "sucesso", "regra A"), c("CT-007", "falha", "regra A")]))
    assert rel.aprovado
    assert any(a.regra == "ids_sequenciais" for a in rel.avisos)


def test_titulo_duplicado_e_aviso():
    rel = auditar(
        suite(
            ["regra A"],
            [
                c("CT-001", "sucesso", "regra A", titulo="Enviar solicitacao"),
                c("CT-002", "falha", "regra A", titulo="Enviar Solicitação"),
            ],
        )
    )
    assert rel.aprovado
    assert any(a.regra == "caso_duplicado" for a in rel.avisos)
