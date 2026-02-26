import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

res = client.chat.completions.create(
    model=model,
    messages=[{"role":"user","content":"Say hello in one short sentence."}]
)

print(res.choices[0].message.content)
