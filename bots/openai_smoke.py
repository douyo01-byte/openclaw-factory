import os
import os

def _load_persona_from_env():
  core=os.environ.get("CORE_PERSONA_FILE")
  role=os.environ.get("PERSONA_FILE")
  t=[]
  if core and os.path.exists(core):
    t.append(open(core,"r",encoding="utf-8").read().strip())
  if role and os.path.exists(role):
    t.append(open(role,"r",encoding="utf-8").read().strip())
  return "\n\n".join([x for x in t if x])

PERSONA=_load_persona_from_env()

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
