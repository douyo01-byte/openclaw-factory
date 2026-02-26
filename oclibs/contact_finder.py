import re
import requests
from urllib.parse import urljoin, urlparse

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)

CANDIDATE_PATHS = [
    "/contact", "/contact-us", "/contacts",
    "/about", "/about-us",
    "/press", "/media",
    "/support", "/help",
    "/privacy", "/terms"
]

def _get(url: str, timeout=20):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml"
    }
    r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r.text, r.url

def _domain(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"

def find_contacts(project_url: str):
    """
    Returns: dict with keys:
      - emails: list[str]
      - contact_pages: list[str]
      - notes: str
    """
    out = {"emails": [], "contact_pages": [], "notes": ""}

    try:
        html, final_url = _get(project_url)
    except Exception as e:
        out["notes"] = f"fetch_failed:{e}"
        return out

    emails = sorted(set(EMAIL_RE.findall(html)))
    if emails:
        out["emails"] = emails[:5]

    base = _domain(final_url)

    # 候補ページをいくつか辿る
    checked = set()
    for path in CANDIDATE_PATHS:
        u = urljoin(base, path)
        if u in checked:
            continue
        checked.add(u)
        try:
            h, fu = _get(u)
        except Exception:
            continue

        if "contact" in fu.lower() or "support" in fu.lower():
            out["contact_pages"].append(fu)

        more = EMAIL_RE.findall(h)
        for em in more:
            if em not in out["emails"]:
                out["emails"].append(em)
        if len(out["emails"]) >= 3:
            break

    out["contact_pages"] = out["contact_pages"][:5]
    out["emails"] = out["emails"][:5]
    return out
