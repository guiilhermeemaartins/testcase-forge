"""Acesso ao modelo de linguagem.

Chamada HTTP direta a API REST, sem SDK: menos dependencia para instalar
e nada que quebre por mudanca de versao de biblioteca.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Protocol

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={chave}"
)


class ErroDoProvider(RuntimeError):
    pass


class Provider(Protocol):
    def gerar(self, prompt: str) -> str:
        """Devolve o texto cru da resposta do modelo."""
        ...


class GeminiProvider:
    """Google Gemini via API REST. A chave vem de GEMINI_API_KEY."""

    def __init__(self, chave: str | None = None, modelo: str | None = None) -> None:
        self.chave = chave or os.environ.get("GEMINI_API_KEY", "")
        # O nome do modelo muda com o tempo; por isso fica configuravel.
        self.modelo = modelo or os.environ.get("FORGE_MODEL", "gemini-3.6-flash")
        if not self.chave:
            raise ErroDoProvider(
                "GEMINI_API_KEY nao definida. Copie .env.example para .env e preencha, "
                "ou rode com --mock para testar sem chave."
            )

    def gerar(self, prompt: str) -> str:
        corpo = {
            "contents": [{"parts": [{"text": prompt}]}],
            # temperatura baixa: aqui nao se quer criatividade, se quer consistencia
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2},
        }
        req = urllib.request.Request(
            GEMINI_URL.format(modelo=self.modelo, chave=self.chave),
            data=json.dumps(corpo).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                dados = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode("utf-8", "replace")[:400]
            raise ErroDoProvider(
                f"HTTP {e.code} do provider. Se for 404, confira o nome do modelo "
                f"em FORGE_MODEL. Detalhe: {detalhe}"
            ) from e
        except urllib.error.URLError as e:
            raise ErroDoProvider(f"Falha de rede ao chamar o provider: {e.reason}") from e

        try:
            return dados["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ErroDoProvider(f"Resposta em formato inesperado: {json.dumps(dados)[:400]}") from e


class MockProvider:
    """Devolve uma resposta fixa. Serve para os testes e para demonstrar
    o fluxo sem depender de rede ou de chave de API."""

    def __init__(self, resposta: str) -> None:
        self.resposta = resposta
        self.chamadas: list[str] = []

    def gerar(self, prompt: str) -> str:
        self.chamadas.append(prompt)
        return self.resposta
