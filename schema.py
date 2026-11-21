import json
from jsonschema import validate, ValidationError

LEVEL = {"type": "integer", "minimum": 0, "maximum": 100}

def _args(**props):
    return {"type": "object", "required": list(props),
            "additionalProperties": False, "properties": props}

def _action(name, args_schema):
    return {"type": "object", "required": ["name", "args"],
            "additionalProperties": False,
            "properties": {"name": {"const": name}, "args": args_schema}}

SCHEMA = {
    "type": "object",
    "required": ["actions"],
    "additionalProperties": False,
    "properties": {
        "actions": {
            "type": "array",
            "items": {"oneOf": [
                _action("set_brightness", _args(level=LEVEL)),
                _action("set_theme", _args(mode={"enum": ["dark", "light"]})),
                _action("set_power_mode", _args(mode={"enum": ["battery_saver", "balanced", "performance"]})),
                _action("set_volume", _args(level=LEVEL)),
                _action("toggle_wifi", _args(enabled={"type": "boolean"})),
            ]},
        }
    },
}

def score(pred_text, gold):
    try:
        pred = json.loads(pred_text)
    except json.JSONDecodeError:
        return {'valid_json': 0, 'valid_schema': 0, 'exact': 0}

    try:
        validate(pred, SCHEMA)
    except ValidationError:
        return {'valid_json': 1, 'valid_schema': 0, 'exact': 0}
    
    return {'valid_json': 1, 'valid_schema':1, 'exact': int(pred == gold)}
