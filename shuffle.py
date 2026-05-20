import json
import pathlib
import random
import sys


def _next_numbered_path(base: pathlib.Path) -> pathlib.Path:
    """Return the first non-existing path of the form <stem>_N<suffix>."""
    n = 1
    while True:
        candidate = base.parent / f"{base.stem}_{n}{base.suffix}"
        if not candidate.exists():
            return candidate
        n += 1


if len(sys.argv) < 2:
    print("Usage: shuffle.py <input_file> [output_file]")
    sys.exit(1)

input_path = pathlib.Path(sys.argv[1])
with open(input_path, "r", encoding="utf-8") as f:
    responses = json.load(f)

random.shuffle(responses)

if len(sys.argv) > 2:
    output_path = pathlib.Path(sys.argv[2])
else:
    output_path = _next_numbered_path(pathlib.Path("data/shuffled_responses.json"))

output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(responses, f, ensure_ascii=False, indent=2)

print(f"Shuffled {len(responses)} responses -> {output_path}")
