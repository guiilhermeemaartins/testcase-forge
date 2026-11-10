"""Contrato de saida do gerador.

A IA nao tem liberdade de formato: ela preenche estas estruturas ou a
resposta e rejeitada. Esse contrato e o que permite auditar a saida
depois, de forma deterministica.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Tipo = Literal["sucesso", "falha", "alternativo"]
Prioridade = Literal["alta", "media", "baixa"]


class Passo(BaseModel):
    acao: str = Field(..., min_length=3, description="O que o testador faz, na voz imperativa")
    dado: Optional[str] = Field(None, description="Massa de dados usada no passo, quando houver")


class CasoDeTeste(BaseModel):
    id: str = Field(..., description="Identificador no padrao CT-001")
    titulo: str = Field(..., min_length=5)
    tipo: Tipo
    prioridade: Prioridade
    regra_coberta: str = Field(..., description="A regra do requisito que este caso verifica")
    pre_condicoes: list[str] = Field(default_factory=list)
    passos: list[Passo] = Field(..., min_length=1)
    resultado_esperado: str = Field(..., min_length=10)

    @field_validator("id")
    @classmethod
    def _padrao_do_id(cls, v: str) -> str:
        import re

        if not re.fullmatch(r"CT-\d{3}", v):
            raise ValueError(f"id fora do padrao CT-000: {v!r}")
        return v


class SuiteDeTestes(BaseModel):
    requisito: str = Field(..., description="Resumo em uma linha do requisito recebido")
    regras_identificadas: list[str] = Field(
        ..., min_length=1, description="As regras testaveis extraidas do requisito"
    )
    casos: list[CasoDeTeste] = Field(..., min_length=1)
