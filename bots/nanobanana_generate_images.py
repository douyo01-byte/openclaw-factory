from __future__ import annotations
import os
import sys
from pathlib import Path

def load_api_key() -> str:
    key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )
    if not key:
        raise SystemExit("missing GEMINI_API_KEY or GOOGLE_API_KEY")
    return key

def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: nanobanana_generate_images.py <prompt_file> <output_path>")

    prompt_file = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    prompt = prompt_file.read_text(encoding="utf-8").strip()
    api_key = load_api_key()
    model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

    from google import genai

    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    for cand in getattr(resp, "candidates", []) or []:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            inline = getattr(part, "inline_data", None)
            data = getattr(inline, "data", None) if inline else None
            if data:
                output_path.write_bytes(data)
                print(str(output_path))
                return

    raise SystemExit("no_image_data_returned")

if __name__ == "__main__":
    main()
