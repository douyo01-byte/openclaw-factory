import re
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

PLATFORM_DOMAINS = {
    "producthunt.com",
    "www.producthunt.com",
    "news.ycombinator.com",
    "hnrss.org",
    "reddit.com",
    "www.reddit.com",
    "kicktraq.com",
    "www.kicktraq.com",
    "indiegogo.com",
    "www.indiegogo.com",
    "kickstarter.com",
    "www.kickstarter.com",
    "backerkit.com",
    "www.backerkit.com",
    "crowdsupply.com",
    "www.crowdsupply.com",
}

EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)

def _domain(u: str) -> str:
    try:
        return urlparse(u).netloc.lower()
    except Exception:
        return ""

def guess_official_site(url: str, html: str) -> str | None:
    d = _domain(url)
    soup = BeautifulSoup(html, "lxml")

    if d not in PLATFORM_DOMAINS:
        return url

    cands = []
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        absu = urljoin(url, href)
        cd = _domain(absu)
        if not cd:
            continue
        if cd in PLATFORM_DOMAINS:
            continue
        if any(x in cd for x in ["twitter.com", "x.com", "facebook.com", "instagram.com"]):
            continue
        cands.append(absu)

    return cands[0] if cands else None

def fetch(url: str, timeout: int = 25) -> str:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text

def extract_emails_from_html(html: str) -> list[str]:
    # 変なエスケープ(u003e...)が混ざることがあるので一旦除去
    html = html.replace("u003e", "").replace("u003c", "")
    emails = sorted(set(EMAIL_RE.findall(html)))
    # 明らかなゴミを弾く
    emails = [e for e in emails if "@" in e and " " not in e and "<" not in e and ">" not in e]
    emails = [e for e in emails if '%' not in e and not any(x in e.lower() for x in ['.png','.jpg','.jpeg','.gif','.svg'])]
    return sorted(set(emails))

def filter_emails_by_domain(emails: list[str], site_url: str) -> list[str]:
    d = _domain(site_url)
    if not d:
        return []
    d2 = d[4:] if d.startswith("www.") else d
    out = []
    for e in emails:
        ed = e.split("@", 1)[1].lower()
        ed2 = ed[4:] if ed.startswith("www.") else ed
        if ed2 == d2:
            out.append(e)
    return sorted(set(out))


def drop_platform_emails(emails: list[str]) -> list[str]:
    bad_domains = set()
    for d in PLATFORM_DOMAINS:
        bad_domains.add(d.lower())
        if d.lower().startswith("www."):
            bad_domains.add(d.lower()[4:])
    out = []
    for e in emails:
        try:
            dom = e.split("@",1)[1].lower()
            dom2 = dom[4:] if dom.startswith("www.") else dom
            if dom in bad_domains or dom2 in bad_domains:
                continue
            out.append(e)
        except Exception:
            continue
    return sorted(set(out))

