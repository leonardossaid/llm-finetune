from schema import score
gold = {"actions": []}
print(score('{"actions": [', gold))
print(score('{"actions": [{"name": "fly", "args": {}}]}', gold))
print(score('{"actions": [{"name": "set_volume", "args": {"foo": 1}}]}', gold))