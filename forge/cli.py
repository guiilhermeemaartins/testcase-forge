"""Linha de comando.

    python -m forge.cli gerar exemplos/01-solicitacao-alvara.md -o saida/alvara.yaml
    python -m forge.cli auditar saida/alvara.yaml
"""

import argparse
import pathlib
import sys

import yaml

from .auditor import auditar, carregar_regras
from .generator import gerar_suite
from .provider import ErroDoProvider, GeminiProvider, MockProvider
from .schema import SuiteDeTestes

RESPOSTA_MOCK = pathlib.Path(__file__).parent.parent / "exemplos" / "resposta-mock.json"


def _escreve(suite: SuiteDeTestes, destino: pathlib.Path | None) -> None:
    texto = yaml.safe_dump(
        suite.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False, width=100
    )
    if destino:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
        print(f"suite escrita em {destino}")
    else:
        print(texto)


def cmd_gerar(args: argparse.Namespace) -> int:
    requisito = pathlib.Path(args.requisito).read_text(encoding="utf-8")

    # As regras extras sao carregadas antes de chamar o modelo: arquivo de
    # regras com erro nao deve gastar uma chamada de API.
    try:
        extras = carregar_regras(args.regras) if args.regras else []
    except ValueError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2

    if args.mock:
        provider = MockProvider(RESPOSTA_MOCK.read_text(encoding="utf-8"))
    else:
        try:
            provider = GeminiProvider()
        except ErroDoProvider as e:
            print(f"erro: {e}", file=sys.stderr)
            return 2

    try:
        suite = gerar_suite(requisito, provider)
    except (ErroDoProvider, ValueError) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2

    print(f"{len(suite.casos)} casos gerados para {len(suite.regras_identificadas)} regras\n")
    _escreve(suite, pathlib.Path(args.saida) if args.saida else None)

    try:
        rel = auditar(suite, extras)
    except ValueError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2
    print("\n--- auditoria ---")
    print(rel.texto())
    # Saida reprovada na auditoria nao e entregue como se estivesse pronta.
    return 1 if not rel.aprovado else 0


def cmd_auditar(args: argparse.Namespace) -> int:
    dados = yaml.safe_load(pathlib.Path(args.suite).read_text(encoding="utf-8"))
    suite = SuiteDeTestes.model_validate(dados)
    try:
        extras = carregar_regras(args.regras) if args.regras else []
        rel = auditar(suite, extras)
    except ValueError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2
    print(rel.texto())
    return 1 if not rel.aprovado else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="forge", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gerar", help="gera casos de teste a partir de um requisito")
    g.add_argument("requisito", help="arquivo .md ou .txt com o criterio de aceite")
    g.add_argument("-o", "--saida", help="arquivo .yaml de saida (padrao: imprime na tela)")
    g.add_argument("--mock", action="store_true", help="usa resposta fixa, sem chamar a API")
    g.add_argument("--regras", help="arquivo .py com regras extras de auditoria")
    g.set_defaults(func=cmd_gerar)

    a = sub.add_parser("auditar", help="audita uma suite .yaml ja gerada")
    a.add_argument("suite")
    a.add_argument("--regras", help="arquivo .py com regras extras de auditoria")
    a.set_defaults(func=cmd_auditar)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
