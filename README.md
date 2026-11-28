# llm-finetune

Fine-tuning de um modelo de linguagem pequeno (**Qwen2.5-1.5B-Instruct**) com **LoRA** para converter pedidos em linguagem natural sobre configurações do PC em **ações JSON estritamente validadas por schema**.

```text
"Dark mode, full brightness, and battery saver please"
```
```json
{"actions": [
  {"name": "set_theme",      "args": {"mode": "dark"}},
  {"name": "set_brightness", "args": {"level": 100}},
  {"name": "set_power_mode", "args": {"mode": "battery_saver"}}
]}
```

O foco do projeto não é só treinar, mas **medir direito**: dataset sintético sem vazamento entre splits, um conjunto de exemplos escritos à mão, scorer em 3 níveis, taxonomia de erros e intervalo de confiança para cada resultado.

> [!NOTE]
> **Status:** dataset, métricas e baseline zero-shot prontos. O script de treino LoRA ainda não está no repositório. O `evaluate.py` já aceita um adapter (`--adapter`) para avaliar o modelo ajustado assim que ele existir.

---

## Sumário

- [A tarefa](#a-tarefa)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Instalação](#instalação)
- [Uso](#uso)
- [Dataset](#dataset)
- [Avaliação](#avaliação)
- [Resultados](#resultados)
- [Roadmap](#roadmap)

---

## A tarefa

O modelo recebe um pedido do usuário e deve responder **apenas** com um objeto JSON `{"actions": [...]}`. Existem 5 ações suportadas:

| Ação             | Argumentos                                                 |
| ---------------- | ---------------------------------------------------------- |
| `set_brightness` | `level`: inteiro de 0 a 100                                |
| `set_theme`      | `mode`: `"dark"` \| `"light"`                              |
| `set_power_mode` | `mode`: `"battery_saver"` \| `"balanced"` \| `"performance"` |
| `set_volume`     | `level`: inteiro de 0 a 100                                |
| `toggle_wifi`    | `enabled`: `true` \| `false`                               |

**Regras de comportamento** (é aqui que modelos base costumam falhar):

- Só agir sobre o que foi pedido **explicitamente**.
- Se faltar um número ou uma direção (`"turn the volume up"`, `"toggle wifi"`), **não gerar ação**.
- Pedidos não suportados (`"turn on bluetooth"`) ou fora de escopo (`"tell me a joke"`) → `{"actions": []}`.
- Pedidos mistos: executar só a parte suportada.
- `mute` = `set_volume` com `level: 0`; `max`/`full` = `100`.
- As ações seguem **a ordem em que aparecem no texto**.

O schema completo (com `additionalProperties: false` e `oneOf` por ação) está em [`schema.py`](schema.py).

---

## Estrutura do repositório

```text
.
├── schema.py            # JSON Schema das ações + score() em 3 níveis
├── common.py            # system prompt e make_example() (formato chat/messages)
├── build_examples.py    # gera data/handwritten.jsonl (20 exemplos escritos à mão)
├── build_dataset.py     # gera train/val/test sintéticos, sem vazamento entre splits
├── check_data.py        # sanity check: o gabarito dos exemplos manuais passa no schema
├── evalkit.py           # taxonomia de erros, strip_fences, IC de Wilson, prompt detalhado
├── evaluate.py          # avaliação em lote na GPU (modelo base ou base + LoRA)
├── explore_tokens.py    # inspeciona o chat template e a contagem de tokens
├── quebra_teste.py      # casos que devem quebrar o scorer (JSON truncado, ação inexistente…)
├── treino_basico.py     # aquecimento: regressão linear com loop de treino em PyTorch
├── tests/
│   └── test_evalkit.py  # testes unitários do classificador de erros e do Wilson
├── data/                # handwritten / train / val / test em JSONL
├── results/             # métricas de cada execução (eval_<tag>__<split>.json)
└── outputs/             # falhas detalhadas por execução (ignorado pelo git)
```

---

## Instalação

Requer Python 3.10+ e uma GPU com CUDA (o `evaluate.py` carrega o modelo em `bfloat16` na `cuda`).

```bash
git clone <url-do-repositorio>
cd llm-finetune

python -m venv .venv
source .venv/bin/activate

pip install torch transformers peft accelerate datasets trl jsonschema pytest
```

Versões usadas no desenvolvimento: Python 3.14, torch 2.15, transformers 5.24, peft 0.22, trl 1.18, datasets 5.2, accelerate 1.16, jsonschema 4.26.

---

## Uso

### 1. Gerar os dados

```bash
python build_examples.py   # data/handwritten.jsonl
python check_data.py       # todos os gabaritos devem pontuar 1/1/1
python build_dataset.py    # data/train.jsonl, data/val.jsonl, data/test.jsonl
```

O `build_dataset.py` usa seed fixa (`42`), então a geração é reprodutível. No final ele imprime a distribuição de cada split e verifica que não há sobreposição entre eles.

### 2. Avaliar

```bash
# baseline zero-shot com o system prompt mínimo (o mesmo do treino)
python evaluate.py --data data/test.jsonl --tag base-minimal

# baseline zero-shot com um system prompt detalhado (schema + regras)
python evaluate.py --data data/test.jsonl --tag base-detailed --prompt detailed

# modelo com adapter LoRA (mesclado antes da inferência)
python evaluate.py --data data/test.jsonl --tag lora --adapter outputs/<adapter>

# teste rápido nos primeiros 32 exemplos (não grava em results/)
python evaluate.py --data data/val.jsonl --tag smoke --limit 32
```

| Argumento   | Padrão                        | Descrição                                       |
| ----------- | ----------------------------- | ----------------------------------------------- |
| `--data`    | obrigatório                   | arquivo JSONL de avaliação                      |
| `--tag`     | obrigatório                   | nome da execução (usado nos arquivos de saída)  |
| `--model`   | `Qwen/Qwen2.5-1.5B-Instruct`  | modelo base do Hugging Face                     |
| `--adapter` | `None`                        | caminho de um adapter LoRA                      |
| `--prompt`  | `minimal`                     | `minimal` ou `detailed`                         |
| `--limit`   | `None`                        | avalia só os N primeiros exemplos               |
| `--batch`   | `16`                          | tamanho do lote na geração                      |

A geração é gulosa (`do_sample=False`, `max_new_tokens=160`), então os resultados são determinísticos.

**Saídas:**
- `results/eval_<tag>__<split>.json`: métricas agregadas.
- `outputs/failures_<tag>__<split>.json`: cada exemplo que errou, com pedido, gabarito, predição e categoria do erro.

### 3. Testes

```bash
pytest -q
```

---

## Dataset

Todos os exemplos usam o formato `messages` (system / user / assistant), pronto para SFT com chat template:

```json
{"messages": [
  {"role": "system",    "content": "Convert PC setting requests into JSON actions."},
  {"role": "user",      "content": "could you please put the laptop in performance mode"},
  {"role": "assistant", "content": "{\"actions\": [{\"name\": \"set_power_mode\", \"args\": {\"mode\": \"performance\"}}]}"}
]}
```

| Split         | Exemplos | 0 ações | 1 ação | 2 ações | 3 ações |
| ------------- | -------: | ------: | -----: | ------: | ------: |
| `train`       |    1 200 |     18% |    49% |     28% |      5% |
| `val`         |      200 |     19% |    50% |     26% |      5% |
| `test`        |      300 |     23% |    46% |     24% |      7% |
| `handwritten` |       20 |     30% |    55% |     10% |      5% |

### Como os dados sintéticos são gerados

- **Bancos de frases** por ação (ex.: 12 jeitos de pedir brilho, 8 de pedir mudo, 10 por modo de energia), além de frases **sem ação** (comandos não suportados ou sem valor, como `"lower the brightness"`) e perguntas **fora de escopo**.
- Cada pedido combina de 1 a 3 fragmentos (pesos 50/35/15), com 25% de chance de cada fragmento ser um no-op. Os fragmentos são unidos com conectores variados (`and`, `and also`, `, then`) e recebem prefixos e sufixos de cortesia (`please`, `can you`, `thanks`…).
- ~6% dos pedidos são perguntas totalmente fora de escopo.

### Prevenção de vazamento

- **Frases diferentes por split:** cada banco é fatiado em ~60% / 20% / 20%. Os templates de teste nunca aparecem no treino, então o teste mede generalização e não memorização.
- **Deduplicação** por texto normalizado (minúsculas, sem pontuação) dentro de cada split.
- **Bloqueio dos exemplos manuais:** nenhum texto de `handwritten.jsonl` pode aparecer nos dados sintéticos.
- **Asserts no final** garantem interseção vazia entre `train`, `val` e `test`.

O `handwritten.jsonl` fica como um conjunto *held-out* de casos escolhidos a dedo: pedidos mistos, `toggle wifi` sem direção, `"wifi on"` curto, espaços duplos etc.

---

## Avaliação

### Scorer em 3 níveis (`schema.score`)

Cada predição recebe três notas cumulativas:

1. **`valid_json`**: a resposta é JSON parseável?
2. **`valid_schema`**: o JSON passa no schema (ações e argumentos permitidos, sem campos extras)?
3. **`exact`**: é idêntico ao gabarito, incluindo ordem e valores?

Cada métrica é reportada em dois modos:
- **strict**: a resposta crua do modelo.
- **lenient**: depois de remover cercas de markdown (` ```json … ``` `), para separar problemas de *formato* de problemas de *conteúdo*.

### Taxonomia de erros (`evalkit.classify`)

| Categoria               | Significado                                              |
| ----------------------- | -------------------------------------------------------- |
| `ok`                    | acerto exato                                             |
| `format_fences`         | JSON correto, mas embrulhado em ` ```json ``` `          |
| `format_invalid_json`   | não vira JSON nem sem as cercas                          |
| `schema_invalid`        | JSON válido, mas ação ou argumento fora do schema        |
| `acted_when_should_not` | o gabarito é `[]` e o modelo inventou ações              |
| `missed_all`            | o gabarito tem ações e o modelo devolveu `[]`            |
| `wrong_action_set`      | ações a mais ou a menos                                  |
| `wrong_order`           | mesmas ações, ordem trocada                              |
| `wrong_args`            | mesmas ações, argumento errado (ex.: 40 em vez de 45)    |

### Intervalo de confiança

A acurácia exata vem acompanhada de um **IC de 95% de Wilson**, que se comporta bem perto de 0% e de 100%. Exemplo: 100% de acerto em n=300 ainda corresponde a um limite inferior de ~98,7%. Os resultados também são separados **pelo número de ações no gabarito** (0, 1, 2, 3).

---

## Resultados

### Baseline zero-shot: `Qwen2.5-1.5B-Instruct`, prompt mínimo, `test` (n=300)

| Modo    | valid_json | valid_schema | exact |
| ------- | ---------: | -----------: | ----: |
| strict  |      28,3% |         0,0% |  0,0% |
| lenient |      90,7% |         0,0% |  0,0% |

- **IC 95% (exact):** [0,0%, 1,3%]
- **Erros:** `format_fences` 187 · `schema_invalid` 85 · `format_invalid_json` 28
- **Tempo:** ~44 s

**Leitura:** só com o system prompt mínimo, o modelo base até produz JSON na maioria das vezes (quase sempre dentro de cercas markdown), mas **nunca** no formato esperado. Ele inventa estruturas próprias como `{"action": "turn_off_wifi"}` ou `{"action": "increase_volume"}`, age em pedidos sem valor e às vezes responde à pergunta (`"tell me a joke"` → conta a piada). Esse é exatamente o comportamento que o fine-tuning precisa corrigir.

| Execução                 | strict exact | IC 95%  | Status   |
| ------------------------ | -----------: | ------- | -------- |
| base + prompt mínimo     |         0,0% | 0–1,3%  | ✅       |
| base + prompt detalhado  |            — | —       | pendente |
| base + LoRA              |            — | —       | pendente |

---

## Roadmap

- [x] Schema JSON e scorer em 3 níveis
- [x] Exemplos escritos à mão + validação
- [x] Dataset sintético com splits sem vazamento
- [x] Taxonomia de erros, IC de Wilson e testes unitários
- [x] Baseline zero-shot (prompt mínimo)
- [ ] Baseline zero-shot com prompt detalhado registrado em `results/`
- [ ] Script de fine-tuning LoRA (SFT com `trl` + `peft`)
- [ ] Avaliação do adapter em `test` e `handwritten`
- [ ] Comparação entre execuções e análise das falhas restantes
- [ ] `requirements.txt` com versões fixadas

---

## Stack

[PyTorch](https://pytorch.org/) · [🤗 Transformers](https://github.com/huggingface/transformers) · [PEFT](https://github.com/huggingface/peft) · [TRL](https://github.com/huggingface/trl) · [jsonschema](https://github.com/python-jsonschema/jsonschema) · [pytest](https://pytest.org/)
