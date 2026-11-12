"""Transforma um requisito em prosa numa suite de testes estruturada."""

import re

from pydantic import ValidationError

from .provider import Provider
from .schema import SuiteDeTestes

PROMPT = """Voce e um analista de QA experiente. Receba o requisito abaixo e produza casos de teste.

REQUISITO
---
{requisito}
---

Faca nesta ordem:
1. Leia o requisito e extraia a lista de REGRAS TESTAVEIS. Uma regra e uma afirmacao
   verificavel por execucao. Se o requisito nao definir uma regra de forma clara, NAO
   invente a regra: deixe de fora.
2. Para cada regra, escreva os casos de teste necessarios. Toda regra precisa de pelo
   menos um caso. Cubra o caminho de sucesso, o de falha e os alternativos que o
   requisito descrever.

Restricoes obrigatorias:
- resultado_esperado deve ser verificavel. Diga o que aparece na tela, o que fica
  gravado ou qual mensagem e exibida. Nunca escreva "funciona corretamente",
  "comporta-se como esperado" ou equivalente.
- Cada passo e uma acao unica na voz imperativa ("Informe o CPF", "Clique em Salvar").
- regra_coberta deve repetir, palavra por palavra, uma das strings de regras_identificadas.
- ids sequenciais no padrao CT-001, CT-002.
- Nao invente campo, tela, mensagem ou regra que o requisito nao mencione.

Responda SOMENTE com um JSON valido neste formato, sem cercas de codigo e sem comentarios:
{{
  "requisito": "resumo em uma linha",
  "regras_identificadas": ["regra 1", "regra 2"],
  "casos": [
    {{
      "id": "CT-001",
      "titulo": "...",
      "tipo": "sucesso|falha|alternativo",
      "prioridade": "alta|media|baixa",
      "regra_coberta": "regra 1",
      "pre_condicoes": ["..."],
      "passos": [{{"acao": "...", "dado": "..."}}],
      "resultado_esperado": "..."
    }}
  ]
}}"""

CORRECAO = """A resposta anterior nao pode ser usada. Erro de validacao:

{erro}

Reenvie a resposta inteira como JSON valido, corrigindo apenas o que o erro aponta.
Mantenha o mesmo conteudo nos campos que estavam certos."""


def _extrai_json(texto: str) -> str:
    """Tira cerca de codigo e texto em volta. O modelo as vezes manda ```json."""
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?\s*", "", texto)
    texto = re.sub(r"\s*```$", "", texto)
    i, f = texto.find("{"), texto.rfind("}")
    return texto[i : f + 1] if i != -1 and f > i else texto


def gerar_suite(requisito: str, provider: Provider, tentativas: int = 2) -> SuiteDeTestes:
    """Gera a suite e valida contra o schema.

    O modelo erra o formato de vez em quando, entao a saida nao e aceita de
    primeira: ela e validada, e no erro o proprio erro de validacao volta para
    o modelo como correcao. Se ainda assim nao passar, falha de forma explicita
    em vez de devolver algo meio certo.
    """
    prompt = PROMPT.format(requisito=requisito.strip())
    ultimo_erro: Exception | None = None

    for n in range(1, tentativas + 1):
        bruto = provider.gerar(prompt)
        try:
            return SuiteDeTestes.model_validate_json(_extrai_json(bruto))
        except (ValidationError, ValueError) as e:
            ultimo_erro = e
            if n == tentativas:
                break
            prompt = (
                PROMPT.format(requisito=requisito.strip())
                + "\n\n"
                + CORRECAO.format(erro=str(e)[:1500])
            )

    raise ValueError(
        f"O modelo nao produziu uma suite valida em {tentativas} tentativas. "
        f"Ultimo erro: {ultimo_erro}"
    )
