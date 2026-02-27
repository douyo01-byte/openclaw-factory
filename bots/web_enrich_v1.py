import argparse, re, sqlite3, time
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

EMAIL_RE=re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)

BAD_DOMAINS=set([
  "reddit.com","www.reddit.com","news.ycombinator.com","github.com","www.github.com",
  "producthunt.com","www.producthunt.com","x.com","twitter.com","facebook.com","instagram.com",
  "tiktok.com","youtube.com","www.youtube.com","medium.com","substack.com"
])

def norm_domain(u:str)->str:
    try:
        return (urlparse(u).netloc or "").lower().lstrip("www.")
    except Exception:
        return ""

def pick_official(results):
    for r in results:
        href=r.get("href") or ""
        d=norm_domain(href)
        if not d:
            continue
        if d in BAD_DOMAINS:
            continue
        return href
    return ""

def fetch(url, timeout=10):
    try:
        r=requests.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code>=400:
            return ""
        ct=(r.headers.get("content-type") or "").lower()
        if "text/html" not in ct and "application/xhtml" not in ct and ct:
            return ""
        return r.text[:300000]
    except Exception:
        return ""

def extract_emails(html):
    return sorted(set(m.group(0) for m in EMAIL_RE.finditer(html or "")))

def find_contact_pages(base_url, html):
    soup=BeautifulSoup(html or "", "lxml")
    links=set()
    for a in soup.find_all("a"):
        href=a.get("href") or ""
        txt=(a.get_text(" ", strip=True) or "").lower()
        if not href:
            continue
        if any(k in href.lower() for k in ["contact","support","about","help","company","privacy"]) or any(k in txt for k in ["contact","support","about","help","company"]):
            links.add(urljoin(base_url, href))
    out=[]
    for u in links:
        d=norm_domain(u)
        if d and d==norm_domain(base_url):
            out.append(u)
    return out[:12]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db", default="data/openclaw.db")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--region", default="jp-jp")
    ap.add_argument("--timelimit", default="m")
    args=ap.parse_args()

    conn=sqlite3.connect(args.db)
    conn.row_factory=sqlite3.Row
    cur=conn.cursor()

    rows=cur.execute("""
    select i.id,i.title,i.url
    from items i
    join opportunity o on o.item_id=i.id
    where coalesce(i.official_url,'')=''
      and coalesce(i.contacts_checked_at,'')=''
    order by i.id
    limit ?
    """,(args.limit,)).fetchall()

    dd=DDGS()

    for r in rows:
        item_id=int(r["id"])
        title=(r["title"] or "").strip()
        seed_url=(r["url"] or "").strip()
        q=title if title else seed_url
        results=[]
        try:
            results=list(dd.text(q + " official site", region=args.region, timelimit=args.timelimit, max_results=8))
        except Exception:
            results=[]
        official=pick_official(results)
        if not official and seed_url:
            official=seed_url

        dom=norm_domain(official)
        cur.execute("update items set official_url=?, official_domain=?, contacts_checked_at=datetime('now') where id=?",(official, dom, item_id))
        conn.commit()

        html=fetch(official)
        emails=set(extract_emails(html))
        for u in find_contact_pages(official, html):
            emails.update(extract_emails(fetch(u)))

        for e in sorted(emails):
            try:
                cur.execute("insert into contacts(item_url,email,source,created_at) values(?,?,?,datetime('now'))",(seed_url or official, e, "web_enrich"))
            except Exception:
                pass
        conn.commit()
        time.sleep(0.3)

    conn.close()

if __name__=="__main__":
    main()
