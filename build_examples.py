import json, os
from common import make_example

examples = [
    make_example('turn on dark mode',
                [{'name': 'set_theme', 'args': {'mode': 'dark'}}]),
    
    make_example('set the volume to 40 and turn off wifi',
                 [{'name': 'set_volume', 'args': {'level': 40}},
                  {'name': 'toggle_wifi', 'args': {'enabled': False}}]),
    
    make_example('what is the capital of France?', []),

    make_example("make the screen darker", []),            # sem número -> []
    
    make_example("connect to bluetooth", []),

    make_example('increase brightness to 80', 
                 [{'name': 'set_brightness', 'args': {'level': 80}}]),

    make_example('Turn on battery saver mode and set the screen timeout to 30 seconds',
                  [{'name': 'set_power_mode', 'args': {'mode': 'battery_saver'}}]),

    make_example('switch to balanced power mode',
                 [{'name': 'set_power_mode', 'args': {'mode': 'balanced'}}]),
    
    make_example('Switch to performance power  mode',
                 [{'name': 'set_power_mode', 'args': {'mode': 'performance'}}]),

        make_example('wifi on',
                 [{'name': 'toggle_wifi', 'args': {'enabled': True}}]),

    make_example('Could you please switch to the light theme?',
                 [{'name': 'set_theme', 'args': {'mode': 'light'}}]),

    make_example('mute',
                 [{'name': 'set_volume', 'args': {'level': 0}}]),

    make_example('crank the volume to the max',
                 [{'name': 'set_volume', 'args': {'level': 100}}]),

    make_example('turn the volume up', []),                  # sem número -> []

    make_example('dark mode, full brightness, and battery saver please',
                 [{'name': 'set_theme', 'args': {'mode': 'dark'}},
                  {'name': 'set_brightness', 'args': {'level': 100}},
                  {'name': 'set_power_mode', 'args': {'mode': 'battery_saver'}}]),  # 3 ações, em ordem

    make_example("I'm about to game, give me max performance and set the volume to 60",
                 [{'name': 'set_power_mode', 'args': {'mode': 'performance'}},
                  {'name': 'set_volume', 'args': {'level': 60}}]),

    make_example('toggle wifi', []),                         # direção não explícita -> []

    make_example('set brightness to 50 and turn on bluetooth',
                 [{'name': 'set_brightness', 'args': {'level': 50}}]),  # misto: só o suportado

    make_example('write me a poem about the sea', []),       # fora de escopo

    make_example('disable wifi and print this document',
                 [{'name': 'toggle_wifi', 'args': {'enabled': False}}]),  # misto: só o suportado
]

os.makedirs('data', exist_ok=True)
with open('data/handwritten.jsonl', 'w') as f:
    for ex in examples:
        f.write(json.dumps(ex, ensure_ascii=False) + '\n')