import json
import math
import re

from schema import score 

DETAILED = """You convert PC setting requests into JSON. Reply with ONLY a JSON object, no explanation, no markdown.
                Format: {"actions": [ ... ]}
                Allowed actions:
                - {"name": "set_brightness", "args": {"level": <integer 0-100>}}
                - {"name": "set_theme", "args": {"mode": "dark" | "light"}}
                - {"name": "set_power_mode", "args": {"mode": "battery_saver" | "balanced" | "performance"}}
                - {"name": "set_volume", "args": {"level": <integer 0-100>}}
                - {"name": "toggle_wifi", "args": {"enabled": true | false}}
                Rules: only act on what the user explicitly asked. If a number or direction is missing, or the request is unsupported or unrelated, produce no action for it. 
                If nothing applies, reply {"actions": []}. Mute means volume level 0. Keep actions in the order they appear in the request.
"""

CATEGORIES = [
    "ok",
    "format_fences",         # JSON correto, mas embrulhado em ```json ... ```
    "format_invalid_json",  # nem com as cercas removidas vira JSON
    "schema_invalid",       # JSON válido, mas ação/argumento fora do schema
    "acted_when_should_not",  # gabarito [] e o modelo inventou ações
    "missed_all",           # gabarito tem ações e o modelo devolveu []
    "wrong_action_set",     # ações a mais ou a menos
    "wrong_order",          # mesmas ações, ordem trocada
    "wrong_args",           # mesmas ações, argumento errado (ex.: 40 em vez de 45)
]

def strip_fences(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

def classify(pred_text, gold):
    text = pred_text.strip()
    try:
        pred = json.loads(text)
    except json.JSONDecodeError:
        try:
            json.loads(strip_fences(text))
            return 'format_fences'
        except json.JSONDecodeError:
            return 'format_invalid_json'
    
    s = score(text, gold)
    if not s['valid_schema']:
        return 'schema_invalid'
    if s['exact']:
        return 'ok'
    pred_actions, gold_actions = pred["actions"], gold["actions"]
    if not gold_actions:
        return 'acted_when_should_not'
    if not pred_actions:
        return 'missed_all'     
    pred_names = [a["name"] for a in pred_actions]
    gold_names = [a["name"] for a in gold_actions]
    if sorted(pred_names) != sorted(gold_names):
        return 'wrong_action_set'
    if pred_names != gold_names:
        return 'wrong_order'
    return 'wrong_args'


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((center - margin) / denom, (center + margin) / denom)