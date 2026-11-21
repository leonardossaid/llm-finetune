import json

SYSTEM_PROMPT = "Convert PC setting requests into JSON actions."

def make_example(user_text, actions):
    answer = json.dumps({"actions": actions}, ensure_ascii=False)
    return {"messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": answer},
    ]}