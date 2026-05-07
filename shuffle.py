import json
import random

with open("responses.json", "r", encoding="utf-8") as f:
    responses = json.load(f)

random.shuffle(responses)

with open("shuffled_responses.json", "w", encoding="utf-8") as f:
    json.dump(responses, f, ensure_ascii=False, indent=2)

print(f"Shuffled {len(responses)} responses -> shuffled_responses.json")
