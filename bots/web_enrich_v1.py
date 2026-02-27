import argparse, re, sqlite3, time
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

EMAIL_RE=re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
SOC_HOSTS={
  "x.com":"x","twitter.com":"x",
  "instagram.com":"instagram",
  "tiktok.com":"tiktok",
  "youtube.com":"youtube","youtu.be":"youtube",
  "facebook.com":"facebook","fb.com":"facebook",
  "linkedin.com":"linkedin",
}

BAD_DOMAINS=set([
  "reddit.com","www.reddit.com","news.ycombinator.com","github.com","www.github.com",
  "producthunt.com","www.producthunt.com","medium.com","substack.com"
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
        if ct and ("text/html" not in ct and "application/xhtml" not in ct):
            return ""
        return r.text[:400000]
    except Exception:
        return ""

def extract_emails(html):
    return sorted(set(m.group(0) for m in EMAIL_RE.finditer(html or "")))

def extract_social_links(base_url, html):
    soup=BeautifulSoup(html or "", "lxml")
    out=[]
    for a in soup.find_all("a"):
        href=a.get("href") or ""
        if not href:
            continue
        u=urljoin(base_url, href)
        d=norm_domain(u)
        if not d:
            continue
        for host,kind in SOC_HOSTS.items():
            if d==host or d.endswith("."+host):
                out.append((kind,u))
                break
    uniq=[]
    seen=set()
    for kind,u in out:
        k=(kind,u)
        if k in seen:
            continue
        seen.add(k)
        uniq.append((kind,u))
    return uniq[:50]

def find_contact_pages(base_url, html):
    soup=BeautifulSoup(html or "", "lxml")
    links=set()
    for a in soup.find_all("a"):
        href=a.get("href") or ""
        txt=(a.get_text(" ", strip=True) or "").lower()
        if not href:
            continue
        h=href.lower()
        if any(k in h for k in ["contact","support","about","help","company","privacy","terms","legal"]) or any(k in txt for k in ["contact","support","about","help","company"]):
            links.add(urljoin(base_url, href))
    out=[]
    base_dom=norm_domain(base_url)
    for u in links:
        if norm_domain(u)==base_dom:
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
            results=list(dd.text(q + " official site", region=args.region, timelimit=args.timelimit, max_results=10))
        except Exception:
            results=[]
        official=pick_official(results) or seed_url
        dom=norm_domain(official)

        cur.execute("update items set official_url=?, official_domain=?, contacts_checked_at=datetime('now') where id=?",(official, dom, item_id))
        conn.commit()

        html0=fetch(official)
        emails=set(extract_emails(html0))
        socials=set(extract_social_links(official, html0))

        for u in find_contact_pages(official, html0):
            h=fetch(u)
            emails.update(extract_emails(h))
            socials.update(extract_social_links(u, h))

        for e in sorted(emails):
            try:
                cur.execute("insert into contacts(item_url,email,source,created_at) values(?,?,?,datetime('now'))",(seed_url or official, e, "web_enrich"))
            except Exception:
                pass

        for kind,u in sorted(socials):
            try:
                cur.execute("insert into contact_points(item_url,kind,value,source,created_at) values(?,?,?,?,datetime('now'))",(seed_url or official, kind, u, "web_enrich"))
            except Exception:
                pass

        conn.commit()
        time.sleep(0.3)

    conn.close()

if __name__=="__main__":
    main()
