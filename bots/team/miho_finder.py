import re, sqlite3
import os

def _load_persona():
  core=os.environ.get("CORE_PERSONA_FILE")
  role=os.environ.get("PERSONA_FILE")
  t=[]
  if core and os.path.exists(core):
    t.append(open(core,"r",encoding="utf-8").read().strip())
  if role and os.path.exists(role):
    t.append(open(role,"r",encoding="utf-8").read().strip())
  return "\n\n".join([x for x in t if x])

PERSONA=_load_persona()

from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

SOC = {
  "instagram":"instagram.com",
  "x":"x.com",
  "twitter":"twitter.com",
  "tiktok":"tiktok.com",
  "facebook":"facebook.com",
  "youtube":"youtube.com",
  "linkedin":"linkedin.com",
  "github":"github.com",
  "discord":"discord.gg",
  "telegram":"t.me",
}

EMAIL_RE = re.compile(r'([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})')

def dom(u: str) -> str:
  try:
    return (urlparse(u).netloc or "").lower().replace("www.","")
  except Exception:
    return ""

def pick_official(item_url: str, html: str) -> str:
  d = dom(item_url)
  if d in ("github.com","egokernel.com","mthds.ai","cifer-security.com","conjure.tech","getpando.ai","codedoc.us","alcazarsec.github.io","playzafiro.com","smmall.cloud","skillsplayground.com","blog.peeramid.xyz"):
    return item_url
  soup = BeautifulSoup(html, "lxml")
  cand = []
  for a in soup.select("a[href]"):
    h = a.get("href","").strip()
    if not h.startswith("http"):
      continue
    hd = dom(h)
    if not hd or hd == d:
      continue
    if hd.endswith("reddit.com") or hd.endswith("producthunt.com") or hd.endswith("hnrss.org") or hd.endswith("ycombinator.com"):
      continue
    cand.append(h)
  if not cand:
    return ""
  return cand[0]

def extract_emails(text: str):
  return sorted(set(m.group(1).lower() for m in EMAIL_RE.finditer(text or "")))

def extract_socials(html: str):
  s = set()
  soup = BeautifulSoup(html, "lxml")
  for a in soup.select("a[href]"):
    h = a.get("href","").strip()
    if not h.startswith("http"):
      continue
    hd = dom(h)
    for k,host in SOC.items():
      if host in hd:
        s.add((k, h.split("?")[0]))
  return sorted(s)

def fetch(url: str):
  r = requests.get(url, timeout=20, headers={"User-Agent":"Mozilla/5.0"})
  if r.status_code >= 400:
    return ""
  return r.text or ""

def main():
  import argparse
  ap = argparse.ArgumentParser()
  ap.add_argument("--db", default="data/openclaw.db")
  ap.add_argument("--limit", type=int, default=50)
  args = ap.parse_args()

  conn = sqlite3.connect(args.db)
  conn.row_factory = sqlite3.Row
  bad = set(r["domain"] for r in conn.execute("select domain from bad_domains"))
  rows = conn.execute(
    "select id,url,title,coalesce(official_url,'') official_url from items where coalesce(url,'')!='' limit ?",
    (args.limit,)
  ).fetchall()

  for it in rows:
    item_id = int(it["id"])
    item_url = it["url"]
    title = it["title"] or ""
    official_url = it["official_url"] or ""

    html = fetch(item_url)
    if not official_url:
      off = pick_official(item_url, html)
      if off and dom(off) not in bad:
        conn.execute("update items set official_url=?, official_domain=? where id=?", (off, dom(off), item_id))
        official_url = off

    emails = set(extract_emails(html))
    if official_url:
      off_html = fetch(official_url)
      emails |= set(extract_emails(off_html))
      socials = extract_socials(off_html)
    else:
      socials = extract_socials(html)

    for e in sorted(emails):
      conn.execute(
        "insert or ignore into contacts(item_url,email,source) values(?,?,?)",
        (item_url, e, "web_enrich"),
      )

    for k,v in socials:
      conn.execute(
        "insert or ignore into contact_points(item_url,kind,value,source) values(?,?,?,?)",
        (item_url, k, v, "web_enrich"),
      )

  conn.commit()
  conn.close()

if __name__=="__main__":
  main()
