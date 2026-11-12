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
| `rastreabilidade` | Nenhum caso aponta para uma regra que não está na lista de regras extraídas | bloqueio |
| `caminho_negativo` | A suíte tem pelo menos um caso de tipo `falha` | bloqueio |
| `resultado_verificavel` | Nenhum resultado esperado usa "funciona corretamente" e afins | bloqueio |
| `ids_unicos` | Não há id repetido | bloqueio |
| `ids_sequenciais` | Os ids seguem CT-001, CT-002… | aviso |
| `caso_duplicado` | Não há dois casos com o mesmo título | aviso |
| `passo_acionavel` | Nenhum passo tem menos de duas palavras (curto demais para descrever uma ação) | aviso |

A auditoria fecha em **aprovado ou reprovado**, como um ciclo de teste normal, e o
CLI retorna código de saída diferente de zero quando reprova — então isso para um
pipeline.

As duas primeiras regras são o motivo do projeto existir. `cobertura` é o buraco
silencioso virando falha explícita. `rastreabilidade` é o inverso: pega o caso de
teste que aponta para uma regra fora da lista que o próprio modelo extraiu — a
suíte contradizendo a si mesma. Ela não detecta uma regra inventada que o modelo
tenha colocado na lista; isso está em "Limites conhecidos".

Além disso, o schema (`forge/schema.py`) é um contrato Pydantic: o modelo não tem
liberdade de formato. Quando a resposta não valida, **o próprio erro de validação
volta para o modelo como correção** (`forge/generator.py`), e se na segunda
tentativa ainda não passar, o programa falha de forma explícita em vez de devolver
algo meio certo.

---

## Como rodar

Precisa de Python 3.10 ou mais novo.

**Instalação**

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows (PowerShell ou cmd)
source .venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
```

**Sem chave de API.** Usa uma resposta fixa; serve para ver o fluxo inteiro:

```bash
python -m forge.cli gerar exemplos/01-solicitacao-alvara.md --mock
```

**Auditar uma suíte pronta.** Também não precisa de chave, e vale para uma suíte
editada à mão. As saídas reais deste repositório servem de entrada:

```bash
python -m forge.cli auditar exemplos/saidas-reais/02-login-por-perfil.yaml
```

**Com o modelo real.** A chave gratuita do Gemini sai em
https://aistudio.google.com/apikey. O programa lê a chave da variável de ambiente
`GEMINI_API_KEY`:

```powershell
# Windows (PowerShell)
$env:GEMINI_API_KEY = "sua-chave"
```

```bash
# Linux / macOS / Git Bash
export GEMINI_API_KEY="sua-chave"
```

```bash
python -m forge.cli gerar exemplos/02-login-por-perfil.md -o saida/login.yaml
```

O modelo padrão é `gemini-3.6-flash`. Nomes de modelo mudam com o tempo: se tomar
HTTP 404, defina `FORGE_MODEL` com um nome válido na documentação do provedor. O
arquivo `.env.example` lista as duas variáveis.

No nível gratuito, o limite encontrado em novembro de 2026 foi de 20 requisições
por dia por modelo. Para experimentar à vontade, use `--mock` e `auditar`.

## Resultado com o modelo real

Os três exemplos foram rodados com `gemini-3.6-flash` em 10 e 11/11/2026. As saídas
estão em `exemplos/saidas-reais/`, sem edição manual.

| Exemplo | Regras extraídas | Casos | Auditoria |
|---|---|---|---|
| 01 — solicitação de alvará | 7 | 7 | aprovado |
| 02 — login por perfil | 7 | 7 | aprovado |
| 03 — upload de documento | 6 | 8 | aprovado |

A auditoria aprovou as três. Lendo as saídas, isto é o que ela **não** viu:

- No login, cada regra recebeu exatamente um caso. A regra do bloqueio após três
  tentativas não tem caso de fronteira (duas tentativas não bloqueiam) nem de
  desbloqueio após 15 minutos. `cobertura` exige só "pelo menos um".
- No login, 8 de 26 passos vieram com `dado: Nenhum`: o modelo preencheu um campo
  opcional com um marcador em vez de omitir.
- No login, o CT-001 espera que "a página principal é exibida", e o requisito não
  fala em página principal.
- No upload, o requisito não define mensagem de erro para formato inválido nem para
  arquivo acima do limite. O modelo não inventou a mensagem, que é o comportamento
  pedido no prompt — mas o buraco do requisito passa sem aviso.

Aprovado na auditoria quer dizer estruturalmente consistente, não bem testado.

## Como incluir a sua regra

As oito regras acima são um ponto de partida. Cada time tem o seu critério do que é
um caso de teste aceitável, então o auditor aceita regras extras sem que ninguém
precise alterar `forge/auditor.py`.

Uma regra extra é uma função Python:

- o nome começa com `regra_`;
- recebe a suíte e devolve uma lista de `Achado(severidade, nome_da_regra, mensagem)`;
- a severidade é `"bloqueio"` (reprova a suíte) ou `"aviso"` (não reprova).

`exemplos/regra_extra.py` traz uma regra pronta, que saiu do defeito visto na saída
real do login: campo `dado` preenchido com "Nenhum". Para ver funcionando, sem
chave de API:

```bash
python -m forge.cli auditar exemplos/saidas-reais/02-login-por-perfil.yaml --regras exemplos/regra_extra.py
```

```
APROVADO com avisos

  [aviso] dado_sem_marcador: CT-001 passo 4 tem dado preenchido com marcador ('Nenhum'); omita o campo quando nao houver dado
  ... (8 avisos no total)
```

Sem `--regras`, a mesma suíte sai como "APROVADO - nenhum achado". A opção vale
também para o comando `gerar`; nesse caso o arquivo de regras é carregado antes da
chamada ao modelo, para que um erro nele não gaste uma requisição.

Uma regra extra que devolve algo que não é um `Achado` interrompe a auditoria com
erro, em vez de ser ignorada.

**Atenção:** carregar um arquivo de regras executa o código que está nele. Só
aponte `--regras` para um arquivo que você escreveu ou leu.

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q
```

39 testes, nenhum deles chama a API. O gerador é testado com um provider mockado,
inclusive o caminho em que **o modelo erra o formato na primeira tentativa e acerta
na segunda** — porque esse caminho é o que acontece na prática e é o que eu mais
precisava garantir.

## Estrutura

```
forge/
  schema.py      contrato de saída (Pydantic) — o que a IA pode devolver
  provider.py    acesso ao modelo via HTTP, sem SDK; + MockProvider para teste
  generator.py   monta o prompt, valida e reenvia o erro de validação ao modelo
  auditor.py     as regras determinísticas sobre a saída + carga de regras extras
  cli.py         linha de comando
exemplos/        três critérios de aceite + a resposta fixa usada no modo mock
  saidas-reais/  as suítes que o modelo real gerou para os três critérios
  regra_extra.py exemplo de regra extra de auditoria
tests/           39 testes, sem rede
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
- Pelo mesmo motivo, ele não detecta **regra inventada**. Se o modelo criar uma
  regra que o requisito não tem e a colocar na lista de regras extraídas, os casos
  que apontam para ela passam em `rastreabilidade`.
- A ligação entre caso e regra é feita por **comparação de texto** (sem acento, caixa
  e pontuação). Se o modelo parafrasear a regra no caso, a auditoria acusa dois
  bloqueios de uma vez — `cobertura` e `rastreabilidade` — para um problema que é
  só de redação.
- `cobertura` exige **um caso por regra, não a quantidade certa**. Suíte aprovada
  pode não ter caso de fronteira, como mostra a seção "Resultado com o modelo real".
- Requisito mal escrito gera caso de teste ruim. O prompt instrui o modelo a não
  inventar regra que o requisito não define, mas não há como verificar isso sem o
  requisito estruturado.
- Testado com três requisitos de exemplo. Não é uma amostra que autorize conclusão
  sobre qualidade média.
