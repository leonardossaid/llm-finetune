import json
from schema import score

with open("data/handwritten.jsonl") as f:
    for i, line in enumerate(f, start=1):
        answer = json.loads(line)["messages"][-1]["content"]
        gold = json.loads(answer)
        print(i, score(answer, gold))