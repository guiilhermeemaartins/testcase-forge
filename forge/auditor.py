"""Auditoria deterministica da saida do modelo.

Gerar casos de teste com IA e a parte facil. O que decide se a saida presta e
a verificacao, e verificacao nao se delega ao mesmo modelo que escreveu: as
regras abaixo sao codigo, roda igual toda vez e nao tem opiniao.

Fecha em aprovado ou reprovado, como um ciclo de teste normal.
"""

import importlib.util
import pathlib
import re
import unicodedata
from typing import Callable

from .schema import SuiteDeTestes

SEVERIDADES = ("bloqueio", "aviso")

# Termos que tornam um resultado esperado inverificavel. Se o resultado diz
# "funciona corretamente", nao da para dizer se passou ou falhou.
TERMOS_VAGOS = [
    "corretamente",
    "adequadamente",
    "como esperado",
    "conforme esperado",
    "sem erros",
    "sem problemas",
    "funcionar normalmente",
    "deve funcionar",
    "tudo ok",
    "com sucesso total",
]

PADRAO_ID = re.compile(r"CT-\d{3}")


class Achado:
    def __init__(self, severidade: str, regra: str, mensagem: str) -> None:
        self.severidade = severidade  # "bloqueio" ou "aviso"
        self.regra = regra
        self.mensagem = mensagem

    def __repr__(self) -> str:
        return f"[{self.severidade}] {self.regra}: {self.mensagem}"


class Relatorio:
    def __init__(self, achados: list[Achado]) -> None:
        self.achados = achados

    @property
    def bloqueios(self) -> list[Achado]:
        return [a for a in self.achados if a.severidade == "bloqueio"]

    @property
    def avisos(self) -> list[Achado]:
        return [a for a in self.achados if a.severidade == "aviso"]

    @property
    def aprovado(self) -> bool:
        return not self.bloqueios

    def texto(self) -> str:
        if self.aprovado and not self.avisos:
            return "APROVADO - nenhum achado."
        linhas = ["APROVADO com avisos" if self.aprovado else "REPROVADO", ""]
        for a in self.bloqueios + self.avisos:
            linhas.append(f"  {a}")
        return "\n".join(linhas)


def _normaliza(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower().strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", "", s)


# Uma regra extra tem o mesmo formato das regras de dentro: recebe a suite e
# devolve os achados. Lista vazia quer dizer que a regra nao encontrou nada.
Regra = Callable[[SuiteDeTestes], list[Achado]]


def carregar_regras(caminho: str) -> list[Regra]:
    """Carrega regras extras de um arquivo .py escrito por quem usa a ferramenta.

    Vale como regra toda funcao do arquivo cujo nome comeca com ``regra_``.
    Atencao: carregar o arquivo executa o codigo dele. So aponte para arquivo
    que voce escreveu ou leu.
    """
    arquivo = pathlib.Path(caminho)
    if not arquivo.is_file():
        raise ValueError(f"arquivo de regras nao encontrado: {caminho}")
    spec = importlib.util.spec_from_file_location(arquivo.stem, arquivo)
    if spec is None or spec.loader is None:
        raise ValueError(f"arquivo de regras precisa ser um .py: {caminho}")
    modulo = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(modulo)
    except Exception as e:
        raise ValueError(f"erro ao carregar o arquivo de regras {caminho}: {e}") from e

    # Ordem alfabetica: a mesma entrada produz sempre o mesmo relatorio.
    regras = [
        f for nome, f in sorted(vars(modulo).items()) if nome.startswith("regra_") and callable(f)
    ]
    if not regras:
        raise ValueError(f"nenhuma funcao com nome comecando em regra_ no arquivo {caminho}")
    return regras


def auditar(suite: SuiteDeTestes, regras_extras: list[Regra] | None = None) -> Relatorio:
    achados: list[Achado] = []

    # 1. Cobertura: toda regra identificada precisa de pelo menos um caso.
    cobertas = {_normaliza(c.regra_coberta) for c in suite.casos}
    for regra in suite.regras_identificadas:
        if _normaliza(regra) not in cobertas:
            achados.append(
                Achado("bloqueio", "cobertura", f"nenhum caso cobre a regra: {regra!r}")
            )

    # 2. Caso o contrario: um caso apontar para regra que nao foi identificada.
    identificadas = {_normaliza(r) for r in suite.regras_identificadas}
    for c in suite.casos:
        if _normaliza(c.regra_coberta) not in identificadas:
            achados.append(
                Achado(
                    "bloqueio",
                    "rastreabilidade",
                    f"{c.id} aponta para regra que nao esta em regras_identificadas: "
                    f"{c.regra_coberta!r}",
                )
            )

    # 3. Caminho negativo: suite sem caso de falha testa so o que funciona.
    if not any(c.tipo == "falha" for c in suite.casos):
        achados.append(
            Achado("bloqueio", "caminho_negativo", "a suite nao tem nenhum caso de tipo 'falha'")
        )

    # 4. Resultado esperado verificavel.
    for c in suite.casos:
        alvo = _normaliza(c.resultado_esperado)
        for termo in TERMOS_VAGOS:
            # \b = fronteira de palavra: "corretamente" nao pode casar dentro
            # de "incorretamente", que e um resultado verificavel.
            if re.search(rf"\b{re.escape(_normaliza(termo))}\b", alvo):
                achados.append(
                    Achado(
                        "bloqueio",
                        "resultado_verificavel",
                        f"{c.id} tem resultado esperado inverificavel ({termo!r}): "
                        f"{c.resultado_esperado!r}",
                    )
                )
                break

    # 5. Ids unicos e sequenciais.
    ids = [c.id for c in suite.casos]
    for dup in {i for i in ids if ids.count(i) > 1}:
        achados.append(Achado("bloqueio", "ids_unicos", f"id repetido: {dup}"))
    esperados = [f"CT-{n:03d}" for n in range(1, len(ids) + 1)]
    if ids != esperados and len(set(ids)) == len(ids):
        achados.append(
            Achado("aviso", "ids_sequenciais", f"ids fora da sequencia: {ids} (esperado {esperados})")
        )

    # 6. Titulos duplicados sugerem caso repetido com outra roupa.
    titulos = [_normaliza(c.titulo) for c in suite.casos]
    for dup in {t for t in titulos if titulos.count(t) > 1}:
        achados.append(Achado("aviso", "caso_duplicado", f"titulo repetido: {dup!r}"))

    # 7. Passo acionavel: precisa de verbo, nao de descricao de estado.
    for c in suite.casos:
        for i, p in enumerate(c.passos, start=1):
            if len(p.acao.split()) < 2:
                achados.append(
                    Achado(
                        "aviso",
                        "passo_acionavel",
                        f"{c.id} passo {i} e curto demais para ser uma acao: {p.acao!r}",
                    )
                )

    # 8. Regras extras, de quem usa a ferramenta. Rodam depois das padrao e
    # entram no mesmo relatorio. Regra que devolve algo que nao e um Achado
    # quebra aqui, em vez de passar em silencio.
    for regra in regras_extras or []:
        for a in regra(suite):
            if not isinstance(a, Achado) or a.severidade not in SEVERIDADES:
                raise ValueError(
                    f"a regra extra {regra.__name__} devolveu algo que nao e um Achado "
                    f"com severidade {SEVERIDADES}: {a!r}"
                )
            achados.append(a)

    return Relatorio(achados)
