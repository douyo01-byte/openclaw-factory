from __future__ import annotations
import subprocess
from pathlib import Path

PAIRS = [
    ("prompts/lp_images/fortune_v1_hero.txt", "data/lp_images/fortune_v1/hero.png"),
    ("prompts/lp_images/fortune_v1_emotion.txt", "data/lp_images/fortune_v1/emotion.png"),
    ("prompts/lp_images/fortune_v1_solution.txt", "data/lp_images/fortune_v1/solution.png"),
    ("prompts/lp_images/fortune_v1_cta.txt", "data/lp_images/fortune_v1/cta.png"),
]

PYTHON = str(Path.home() / "AI/openclaw-factory-daemon/.venv/bin/python")

def main():
    for prompt, out in PAIRS:
        subprocess.run([PYTHON, "bots/nanobanana_generate_images.py", prompt, out], check=True)
    print("nanobanana_lp_images_done")

if __name__ == "__main__":
    main()
