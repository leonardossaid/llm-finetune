import argparse
import json
import os 
import time
from collections import defaultdict, Counter

from peft import PeftModel
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

from evalkit import CATEGORIES, DATAILED, DETAILED, classify, strip_fences, wilson
from schema import score

ap = argparse.ArgumentParser()
ap.add_argument('--data', required=True, help='Path to the evaluation data. Ex.: data/test.jsonl')
ap.add_argument('--tag', required=True, help='Name of the evaluation run. Ex.: base-minimal')
ap.add_argument('--model', default='Qwen/Qwen2.5-1.5B-Instruct')
ap.add_argument('--adapter', default=None, help='Path to LoRA adapter. ex.: outputs/ref')
ap.add_argument('--prompt', choices=['minimal', 'detailed'], default=['minimal'])
ap.add_argument('--limit', type=int, default=None, help='Fast evaluation mode. Limit the number of first examples to evaluate.')
ap.add_argument('--batch', type=int, default=16)
args = ap.parse_args()

rows = [json.loads(line) for line in open(args.data)]
if args.limit:
    rows = rows[:args.limit]

tok = AutoTokenizer.from_pretrained(args.model)
tok.padding_side = 'left'
model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16).to('cuda')
if args.adapter:
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, args.adapter)
    model = model.merge_and_unload()
model.eval()

def prompt_for(row):
    msg = row['messages'][:2]
    if args.prompt == 'detailed':
        msgs = [{'role': 'system', 'content': DETAILED}, msgs[1]]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

keys = ['valid_json', 'valid_schema', 'exact']
strict = Counter()
lenient = Counter()
cats = Counter()
by_n = defaultdict(lambda: [0, 0])
failures = []

t0 = time.time()
for i in range(0, len(rows), args.batch):
    batch = rows[i:i + args.batch]
    inputs = tok([prompt_for(r) for r in batch], return_tensors='pt', padding=True, add_special_tokens=False).to('cuda')
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=160, do_sample=False)
    texts = tok.batch_decode(out[:, inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    for r, text in zip(batch, texts):
        gold = json.loads(r['messages'][2]['content'])
        s, l = score(text, gold), score(strip_fences(text), gold)
        for k in keys:
            strict[k] += s[k]
            lenient[k] += l[k]
        c = classify(text, gold)
        cats[c] += 1
        n_gold = len(gold["actions"])
        by_n[n_gold][0] += int(c == "ok")
        by_n[n_gold][1] += 1
        if c != "ok":
            failures.append({"user": r["messages"][1]["content"], "gold": gold,
                             "pred": text, "category": c})
elapsed = time.time() - t0

n = len(rows)
lo, hi = wilson(strict["exact"], n)
result = {
    "kind": "eval", "tag": args.tag, "model": args.model, "adapter": args.adapter,
    "prompt": args.prompt, "data": args.data, "n": n,
    "strict": {k: strict[k] / n for k in keys},
    "lenient": {k: lenient[k] / n for k in keys},
    "exact_ci95": [lo, hi],
    "by_gold_actions": {str(k): {"exact": v[0] / v[1], "n": v[1]} for k, v in sorted(by_n.items())},
    "error_categories": {c: cats[c] for c in CATEGORIES if cats[c]},
    "seconds": round(elapsed, 1),
}

stem = os.path.basename(args.data).replace(".jsonl", "")
if args.limit is None:                   # testes rápidos (--limit) não gravam resultado
    os.makedirs("results", exist_ok=True)
    with open(f"results/eval_{args.tag}__{stem}.json", "w") as f:
        json.dump(result, f, indent=2)
os.makedirs("outputs", exist_ok=True)
with open(f"outputs/failures_{args.tag}__{stem}.json", "w") as f:
    json.dump(failures, f, indent=2, ensure_ascii=False)

print(f"\n{args.tag} | {args.data} | n={n} | {elapsed:.0f}s")
print(f"strict  : " + "  ".join(f"{k}={strict[k] / n:.1%}" for k in keys))
print(f"lenient : " + "  ".join(f"{k}={lenient[k] / n:.1%}" for k in keys))
print(f"exact (strict) 95% CI: [{lo:.1%}, {hi:.1%}]")
print("por nº de ações no gabarito:",
      {k: f"{v[0]}/{v[1]}" for k, v in sorted(by_n.items())})
print("erros:", {c: cats[c] for c in CATEGORIES if cats[c] and c != "ok"})
print(f"falhas salvas em outputs/failures_{args.tag}__{stem}.json")