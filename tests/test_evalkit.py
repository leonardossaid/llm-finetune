import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evalkit import CATEGORIES, classify, strip_fences, wilson
from schema import score

VOL40 = {"name": "set_volume", "args": {"level": 40}}
WIFI_OFF = {"name": "toggle_wifi", "args": {"enabled": False}}
DARK = {"name": "set_theme", "args": {"mode": "dark"}}


def dump(actions):
    return json.dumps({"actions": actions})


def test_ok():
    gold = {"actions": [VOL40, WIFI_OFF]}
    assert classify(dump([VOL40, WIFI_OFF]), gold) == "ok"
    assert classify(dump([]), {"actions": []}) == "ok"


def test_format_errors():
    gold = {"actions": [VOL40]}
    assert classify("```json\n" + dump([VOL40]) + "\n```", gold) == "format_fences"
    assert classify("Sure! Here you go: " + dump([VOL40]), gold) == "format_invalid_json"
    assert classify('{"actions": [', gold) == "format_invalid_json"
    assert classify("", gold) == "format_invalid_json"


def test_schema_invalid():
    gold = {"actions": [VOL40]}
    assert classify(dump([{"name": "fly", "args": {}}]), gold) == "schema_invalid"
    assert classify(dump([{"name": "set_volume", "args": {"foo": 1}}]), gold) == "schema_invalid"
    assert classify(dump([{"name": "set_volume", "args": {"level": 150}}]), gold) == "schema_invalid"
    assert classify("[]", gold) == "schema_invalid"          # JSON válido, mas não é um objeto
    assert classify('{"actions": [], "note": "ok"}', gold) == "schema_invalid"


def test_behavior_errors():
    assert classify(dump([VOL40]), {"actions": []}) == "acted_when_should_not"
    assert classify(dump([]), {"actions": [VOL40]}) == "missed_all"
    assert classify(dump([VOL40]), {"actions": [VOL40, WIFI_OFF]}) == "wrong_action_set"
    assert classify(dump([VOL40, WIFI_OFF, DARK]), {"actions": [VOL40, WIFI_OFF]}) == "wrong_action_set"
    assert classify(dump([DARK]), {"actions": [VOL40]}) == "wrong_action_set"
    assert classify(dump([WIFI_OFF, VOL40]), {"actions": [VOL40, WIFI_OFF]}) == "wrong_order"
    other = {"name": "set_volume", "args": {"level": 45}}
    assert classify(dump([other]), {"actions": [VOL40]}) == "wrong_args"


def test_every_category_is_reachable_and_listed():
    cases = {
        "ok": (dump([]), {"actions": []}),
        "format_fences": ("```\n" + dump([]) + "\n```", {"actions": []}),
        "format_invalid_json": ("nope", {"actions": []}),
        "schema_invalid": ('{"foo": 1}', {"actions": []}),
        "acted_when_should_not": (dump([VOL40]), {"actions": []}),
        "missed_all": (dump([]), {"actions": [VOL40]}),
        "wrong_action_set": (dump([DARK]), {"actions": [VOL40]}),
        "wrong_order": (dump([WIFI_OFF, VOL40]), {"actions": [VOL40, WIFI_OFF]}),
        "wrong_args": (dump([{"name": "set_volume", "args": {"level": 1}}]), {"actions": [VOL40]}),
    }
    assert set(cases) == set(CATEGORIES)
    for expected, (pred, gold) in cases.items():
        assert classify(pred, gold) == expected, expected


def test_classify_agrees_with_score():
    """'ok' <=> exact=1, e as categorias de formato/schema <=> degraus do score."""
    gold = {"actions": [VOL40]}
    for pred in [dump([VOL40]), dump([]), '{"actions": [', dump([{"name": "fly", "args": {}}])]:
        s = score(pred, gold)
        c = classify(pred, gold)
        assert (c == "ok") == bool(s["exact"])
        if not s["valid_json"]:
            assert c.startswith("format_")
        elif not s["valid_schema"]:
            assert c == "schema_invalid"


def test_strip_fences():
    assert strip_fences("```json\n{}\n```") == "{}"
    assert strip_fences("```\n{}\n```") == "{}"
    assert strip_fences("  {}  ") == "{}"


def test_wilson():
    lo, hi = wilson(0, 0)
    assert (lo, hi) == (0.0, 0.0)
    lo, hi = wilson(50, 100)
    assert abs(lo - 0.4038) < 1e-3 and abs(hi - 0.5962) < 1e-3   # valor de referência conhecido
    lo, hi = wilson(300, 300)
    assert hi == 1.0 or abs(hi - 1.0) < 1e-9
    assert 0.98 < lo < 1.0                                          # 100% com n=300 NÃO é certeza
    lo, hi = wilson(255, 300)                                       # 85% com n=300
    assert 0.80 < lo < 0.85 < hi < 0.89