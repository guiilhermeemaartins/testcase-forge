"""Exemplo de regra extra de auditoria.

    python -m forge.cli auditar exemplos/saidas-reais/02-login-por-perfil.yaml --regras exemplos/regra_extra.py

Para escrever a sua, copie este arquivo e troque a funcao. O contrato e:

- o nome da funcao comeca com ``regra_``;
- ela recebe a suite (``forge.schema.SuiteDeTestes``);
- ela devolve uma lista de ``Achado(severidade, nome_da_regra, mensagem)``,
  com severidade "bloqueio" (reprova a suite) ou "aviso" (nao reprova).
  Lista vazia quer dizer que a regra nao encontrou nada.

Esta regra saiu de um defeito visto em saida real: no exemplo do login, o
modelo preencheu o campo opcional ``dado`` de 8 passos com "Nenhum" em vez de
omitir o campo. Marcador nao e massa de dados: polui o caso de teste e
esconde quais passos realmente usam dado.
"""

from forge.auditor import Achado

MARCADORES = {"nenhum", "nenhuma", "n/a", "-", "nao se aplica", "não se aplica"}


def regra_dado_sem_marcador(suite):
    achados = []
    for caso in suite.casos:
        for i, passo in enumerate(caso.passos, start=1):
            if passo.dado is not None and passo.dado.strip(" .").lower() in MARCADORES:
                achados.append(
                    Achado(
                        "aviso",
                        "dado_sem_marcador",
                        f"{caso.id} passo {i} tem dado preenchido com marcador "
                        f"({passo.dado!r}); omita o campo quando nao houver dado",
                    )
                )
    return achados
