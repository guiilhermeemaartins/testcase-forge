"""Auditoria deterministica da saida do modelo.

Gerar casos de teste com IA e a parte facil. O que decide se a saida presta e
a verificacao, e verificacao nao se delega ao mesmo modelo que escreveu: as
regras abaixo sao codigo, roda igual toda vez e nao tem opiniao.

Fecha em aprovado ou reprovado, como um ciclo de teste normal.
"""

import re
import unicodedata

from .schema import SuiteDeTestes

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


def auditar(suite: SuiteDeTestes) -> Relatorio:
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

    return Relatorio(achados)
