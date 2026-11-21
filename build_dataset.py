import json
import os
import random
from collections import Counter

from common import make_example
from schema import score

SIZES = {"train": 1200, "val": 200, "test": 300}

def sub(bank, split):
    """Cada split usa frases DIFERENTES: ~60% treino, ~20% val, ~20% teste."""
    n = len(bank)
    assert n >= 4, "cada banco precisa de pelo menos 4 frases"
    a = max(1, round(n * 0.6))
    b = max(a + 1, round(n * 0.8))
    return {"train": bank[:a], "val": bank[a:b], "test": bank[b:]}[split]

# ---- bancos de frases (todas no imperativo, para combinar com os prefixos) ----
BRIGHT = ["set brightness to {n}", "set the screen brightness to {n}%",
          "put the brightness at {n} percent", "change the brightness to {n}",
          "adjust the brightness to {n}", "make the brightness {n}",
          "bring the brightness to {n}%", "set my screen brightness to {n} percent",
          "put the screen at {n}% brightness", "set the display brightness to {n}",
          "turn the brightness to {n}", "change the screen brightness to {n}"]
BRIGHT_MAX = ["set brightness to max", "put the brightness at maximum",
              "set the screen to full brightness", "crank the brightness to the max",
              "set the brightness to the maximum", "put the screen at full brightness",
              "max out the brightness", "set the display to maximum brightness"]
THEME = {
    "dark": ["turn on dark mode", "switch to the dark theme", "enable dark mode",
             "use the dark theme", "change to dark mode", "set the theme to dark",
             "activate dark mode", "switch to dark mode", "put the system in dark mode",
             "change the theme to dark"],
    "light": ["turn on light mode", "switch to the light theme", "enable light mode",
              "use the light theme", "change to light mode", "set the theme to light",
              "activate light mode", "switch to light mode", "put the system in light mode",
              "change the theme to light"],
}
POWER = {
    "battery_saver": ["turn on battery saver", "enable battery saver mode",
                      "switch to battery saver", "activate the battery saver", "save battery",
                      "set the power mode to battery saver", "put the laptop in battery saver mode",
                      "switch to power saving mode", "go into battery saver mode",
                      "change the power plan to battery saver"],
    "balanced": ["switch to balanced mode", "set the power mode to balanced",
                 "use the balanced power plan", "enable balanced mode",
                 "change the power plan to balanced", "put the laptop in balanced mode",
                 "go back to balanced mode", "activate balanced mode",
                 "switch to the balanced power plan", "set the power plan to balanced"],
    "performance": ["switch to performance mode", "set the power mode to performance",
                    "enable high performance mode", "give me maximum performance",
                    "use the performance power plan", "put the laptop in performance mode",
                    "activate performance mode", "change the power plan to high performance",
                    "set the power plan to performance", "go to max performance mode"],
}
VOL = ["set the volume to {n}", "put the volume at {n} percent",
       "change the volume to {n}", "adjust the volume to {n}%",
       "make the volume {n}", "bring the volume to {n}",
       "set my volume to {n} percent", "turn the volume to {n}",
       "put the sound at {n}%", "set the sound level to {n}"]
MUTE = ["mute", "mute the sound", "mute the audio", "mute my laptop",
        "silence the speakers", "turn off the sound", "mute the volume", "kill the sound"]
VOL_MAX = ["set the volume to max", "crank the volume to the max",
           "put the volume at maximum", "set the volume to full",
           "max out the volume", "set the volume to the maximum",
           "put the sound at full volume", "set the volume to the highest level"]
WIFI = {
    True: ["turn on wifi", "enable wifi", "switch the wifi on", "turn the wifi on",
           "activate wifi", "turn wifi on", "turn on the Wi-Fi", "switch on the wifi"],
    False: ["turn off wifi", "disable wifi", "switch the wifi off", "turn the wifi off",
            "deactivate wifi", "turn wifi off", "turn off the Wi-Fi", "switch off the wifi"],
}
# fragmentos que NÃO geram ação: não suportados OU sem valor suficiente
NOOP = ["turn on bluetooth", "print this document", "set the screen timeout to 30 seconds",
        "open spotify", "restart the computer", "take a screenshot", "set an alarm for 7am",
        "connect to the printer", "turn the volume up", "turn the volume down",
        "make the screen darker", "make the screen brighter", "toggle wifi",
        "dim the screen", "lower the brightness", "make it louder",
        "increase the volume a bit", "turn on airplane mode", "open chrome",
        "lock the screen", "put the computer to sleep", "connect to the vpn",
        "turn on do not disturb", "make the text bigger", "turn on the keyboard backlight",
        "update my drivers", "close all windows", "empty the recycle bin",
        "raise the brightness", "make it quieter", "change the wallpaper",
        "check for updates", "shut down the laptop"]
# frases inteiras fora de escopo
STANDALONE = ["what is the capital of Spain?", "tell me a joke", "what's 15 times 12?",
              "how do I bake bread?", "who painted the Mona Lisa?",
              "translate 'good morning' into German", "what's the weather like today?",
              "write a short story about a dragon", "explain how photosynthesis works",
              "recommend a good movie", "how tall is Mount Everest?",
              "give me a recipe for pancakes", "how many days are in a leap year?",
              "explain what a neural network is", "what's the square root of 144?",
              "suggest a name for my cat", "how do I learn python?",
              "summarize the plot of Hamlet", "convert 50 fahrenheit to celsius",
              "how far is the moon from earth?", "give me tips for a job interview",
              "tell me a fun fact", "how do I change a flat tire?", 
              "what's the difference between a virus and a bacteria?",
              "write a haiku about autumn", "who wrote Don Quixote?",
              "what's the best way to learn spanish?", "how does a bill become a law?",
              "what's the population of Brazil?", "help me write a cover letter",
              "what is the speed of light?", "why is the sky blue?"]
random.Random(0).shuffle(NOOP)
random.Random(0).shuffle(STANDALONE)

LEVELS = list(range(5, 101, 5))

# ---- geradores: devolvem (fragmento de texto, lista de ações) ----
def gen_brightness(rng, split):
    if rng.random() < 0.15:
        return rng.choice(sub(BRIGHT_MAX, split)), [{"name": "set_brightness", "args": {"level": 100}}]
    n = rng.choice(LEVELS)
    return (rng.choice(sub(BRIGHT, split)).format(n=n),
            [{"name": "set_brightness", "args": {"level": n}}])

def gen_theme(rng, split):
    mode = rng.choice(["dark", "light"])
    return rng.choice(sub(THEME[mode], split)), [{"name": "set_theme", "args": {"mode": mode}}]

def gen_power(rng, split):
    mode = rng.choice(list(POWER))
    return rng.choice(sub(POWER[mode], split)), [{"name": "set_power_mode", "args": {"mode": mode}}]

def gen_volume(rng, split):
    r = rng.random()
    if r < 0.10:
        return rng.choice(sub(MUTE, split)), [{"name": "set_volume", "args": {"level": 0}}]
    if r < 0.20:
        return rng.choice(sub(VOL_MAX, split)), [{"name": "set_volume", "args": {"level": 100}}]
    n = rng.choice(LEVELS)
    return (rng.choice(sub(VOL, split)).format(n=n),
            [{"name": "set_volume", "args": {"level": n}}])

def gen_wifi(rng, split):
    on = rng.choice([True, False])
    return rng.choice(sub(WIFI[on], split)), [{"name": "toggle_wifi", "args": {"enabled": on}}]

def gen_noop(rng, split):
    return rng.choice(sub(NOOP, split)), []

# ---- montagem do pedido ----
PREFIXES = ["", "", "please ", "can you ", "could you please ", "hey, ", "I want you to "]
SUFFIXES = ["", "", "", " please", " now", "!", " thanks"]

def join(frags, rng):
    if len(frags) == 1:
        return frags[0]
    if len(frags) == 2:
        return rng.choice([" and ", " and also ", ", then "]).join(frags)
    return ", ".join(frags[:-1]) + rng.choice([" and ", ", then "]) + frags[-1]

def wrap(text, rng):
    text = rng.choice(PREFIXES) + text + rng.choice(SUFFIXES)
    if rng.random() < 0.3:
        text = text[0].upper() + text[1:]
    return text

def make_request(rng, split):
    if rng.random() < 0.06:
        q = rng.choice(sub(STANDALONE, split))
        text = rng.choice(["", "", "hey, ", "quick question: ", "just curious, "]) + q
        return text + rng.choice(["", "", " thanks"]), []
    k = rng.choices([1, 2, 3], weights=[50, 35, 15])[0]
    pool = [gen_brightness, gen_theme, gen_power, gen_volume, gen_wifi]
    rng.shuffle(pool)   # cada ação aparece no máximo uma vez por pedido
    frags, actions = [], []
    for _ in range(k):
        if rng.random() < 0.25:
            frag, acts = gen_noop(rng, split)
        else:
            frag, acts = pool.pop()(rng, split)
        if frag in frags:
            continue
        frags.append(frag)
        actions.extend(acts)   # a ordem das ações = a ordem no texto
    return wrap(join(frags, rng), rng), actions

def norm(s):
    return " ".join(s.lower().replace("?", "").replace("!", "").replace(",", "").split())

def build_split(split, n, rng, blocked):
    out, seen, tries = [], set(), 0
    while len(out) < n and tries < n * 100:
        tries += 1
        text, actions = make_request(rng, split)
        key = norm(text)
        if key in seen or key in blocked:
            continue
        seen.add(key)
        out.append(make_example(text, actions))
    return out

if __name__ == "__main__":
    rng = random.Random(42)
    with open("data/handwritten.jsonl") as f:
        blocked = {norm(json.loads(line)["messages"][1]["content"]) for line in f}
    texts = {}
    for split, n in SIZES.items():
        rows = build_split(split, n, rng, blocked)
        with open(f"data/{split}.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        texts[split] = {norm(r["messages"][1]["content"]) for r in rows}
        bad = noop = multi = 0
        names = Counter()
        for r in rows:
            answer = r["messages"][2]["content"]
            gold = json.loads(answer)
            if score(answer, gold)["valid_schema"] != 1:
                bad += 1
            acts = gold["actions"]
            noop += len(acts) == 0
            multi += len(acts) >= 2
            names.update(a["name"] for a in acts)
        print(f"{split:5} n={len(rows)} | vazias={noop/len(rows):.0%} | "
              f"2+ ações={multi/len(rows):.0%} | schema inválido={bad}")
        print("      ações:", dict(names))
    assert not (texts["train"] & texts["val"]), "vazamento train/val"
    assert not (texts["train"] & texts["test"]), "vazamento train/test"
    assert not (texts["val"] & texts["test"]), "vazamento val/test"
    print("sem sobreposição entre os splits")
