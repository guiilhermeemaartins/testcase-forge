# testcase-forge

Transforma critério de aceite em casos de teste estruturados usando um modelo de
linguagem, e **audita a saída da IA com regras determinísticas** antes de aceitá-la.

```
critério de aceite (texto)  →  LLM  →  schema validado  →  auditoria  →  pass / fail
```

---

## O problema

Trabalho como analista de QA. A parte lenta do meu dia não é executar teste — é a
etapa anterior: ler um critério de aceite escrito em prosa e transformá-lo em um
conjunto completo de casos de teste.

Essa etapa tem dois defeitos conhecidos:

1. **É inconsistente.** Dois analistas lendo o mesmo critério produzem coberturas
   diferentes. Um lembra do caminho de falha, o outro esquece.
2. **Falha por omissão, e a omissão é silenciosa.** Uma regra do requisito que
   ninguém transformou em caso de teste não aparece em lugar nenhum. Não existe
   erro, existe um buraco.

O segundo defeito é o que me incomoda de verdade. Suíte incompleta passa 100% dos
testes.

## Por que IA faz sentido aqui

A tarefa é exatamente onde um modelo de linguagem é bom: **texto natural ambíguo
entrando, estrutura saindo**. Extrair regras testáveis de um parágrafo e enumerar
variações é reconhecimento de padrão em linguagem, não cálculo nem decisão.

E faz sentido também pelo custo do erro. A saída aqui é um **rascunho revisado por
um humano antes de virar caso de teste de verdade**. Se a IA erra, um analista
corrige em um minuto; ninguém vai para produção por causa disso. É o cenário ideal
para usar IA: ganho alto de velocidade, erro barato e reversível.

O que a IA **não** faz neste projeto é decidir se a saída presta. Isso é código.

## O que diferencia este projeto do "chamei a API e pedi casos de teste"

A camada que importa é o **auditor** (`forge/auditor.py`). Ele roda sobre a saída do
modelo e aplica regras que são código, não prompt — rodam igual toda vez e não têm
opinião:

| Regra | O que verifica | Severidade |
|---|---|---|
| `cobertura` | Toda regra extraída do requisito tem pelo menos um caso de teste | bloqueio |
| `rastreabilidade` | Nenhum caso aponta para uma regra que não foi extraída (IA inventou) | bloqueio |
| `caminho_negativo` | A suíte tem pelo menos um caso de tipo `falha` | bloqueio |
| `resultado_verificavel` | Nenhum resultado esperado usa "funciona corretamente" e afins | bloqueio |
| `ids_unicos` | Não há id repetido | bloqueio |
| `ids_sequenciais` | Os ids seguem CT-001, CT-002… | aviso |
| `caso_duplicado` | Não há dois casos com o mesmo título | aviso |
| `passo_acionavel` | Todo passo é uma ação, não uma descrição de estado | aviso |

A auditoria fecha em **aprovado ou reprovado**, como um ciclo de teste normal, e o
CLI retorna código de saída diferente de zero quando reprova — então isso para um
pipeline.

As duas primeiras regras são o motivo do projeto existir. `cobertura` é o buraco
silencioso virando falha explícita. `rastreabilidade` é o inverso: pega a IA
inventando regra que o requisito não tem, que é o jeito mais comum de ela parecer
útil e estar errada.

Além disso, o schema (`forge/schema.py`) é um contrato Pydantic: o modelo não tem
liberdade de formato. Quando a resposta não valida, **o próprio erro de validação
volta para o modelo como correção** (`forge/generator.py`), e se na segunda
tentativa ainda não passar, o programa falha de forma explícita em vez de devolver
algo meio certo.

---

## Como rodar

```bash
pip install -r requirements.txt

# sem chave de API, com resposta fixa — serve para ver o fluxo
python -m forge.cli gerar exemplos/01-solicitacao-alvara.md --mock

# de verdade
cp .env.example .env     # preencha GEMINI_API_KEY
export $(cat .env | xargs)
python -m forge.cli gerar exemplos/02-login-por-perfil.md -o saida/login.yaml

# auditar uma suíte já gerada (inclusive uma editada à mão)
python -m forge.cli auditar saida/login.yaml
```

A chave gratuita do Gemini sai em https://aistudio.google.com/apikey. Nomes de
modelo mudam com o tempo: se tomar HTTP 404, troque `FORGE_MODEL` no `.env` pelo
nome que estiver válido na documentação do provedor.

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q
```

26 testes, nenhum deles chama a API. O gerador é testado com um provider mockado,
inclusive o caminho em que **o modelo erra o formato na primeira tentativa e acerta
na segunda** — porque esse caminho é o que acontece na prática e é o que eu mais
precisava garantir.

## Estrutura

```
forge/
  schema.py      contrato de saída (Pydantic) — o que a IA pode devolver
  provider.py    acesso ao modelo via HTTP, sem SDK; + MockProvider para teste
  generator.py   monta o prompt, valida e reenvia o erro de validação ao modelo
  auditor.py     as regras determinísticas sobre a saída
  cli.py         linha de comando
exemplos/        três critérios de aceite + a resposta fixa usada no modo mock
tests/           26 testes, sem rede
```

## Decisões que tomei de propósito

- **HTTP direto, sem SDK.** Uma dependência a menos para instalar e nada que quebre
  por mudança de versão de biblioteca.
- **`temperature` 0.2.** Aqui não se quer criatividade, se quer consistência.
- **YAML na saída, não JSON.** O arquivo é para ser lido e editado por um analista.
- **Avisos não reprovam.** Id fora de sequência não torna a suíte inútil; regra sem
  caso, sim. Separar as duas coisas é o que faz o relatório ser levado a sério.

## Limites conhecidos

- O auditor verifica **estrutura e cobertura das regras que o modelo extraiu** — ele
  não sabe se o modelo deixou de extrair uma regra do texto original. Fechar essa
  volta exigiria uma segunda extração independente e comparação entre as duas; é o
  próximo passo natural.
- Requisito mal escrito gera caso de teste ruim. O prompt instrui o modelo a não
  inventar regra que o requisito não define, mas não há como verificar isso sem o
  requisito estruturado.
- Testado com três requisitos de exemplo. Não é uma amostra que autorize conclusão
  sobre qualidade média.
