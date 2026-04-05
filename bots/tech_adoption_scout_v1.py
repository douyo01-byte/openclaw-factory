import re, sqlite3, subprocess, json, time
from urllib.request import urlopen

DB = "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def conn():
    return sqlite3.connect(DB)



def fetch_github_trending():
    try:
        html = urlopen("https://github.com/trending").read().decode()

        pairs = re.findall(
            r'<h2[^>]*>.*?<a[^>]*href="/([^"/]+/[^"/]+)"[^>]*>',
            html,
            re.S
        )

        clean = []
        for r in pairs:
            if any(x in r.lower() for x in ["explore", "topics", "collections"]):
                continue
            if "/" not in r:
                continue
            owner, repo = r.split("/", 1)
            if not owner or not repo:
                continue
            clean.append(f"{owner}/{repo}")

        uniq = list(dict.fromkeys(clean))[:10]

        return [
            {
                "title": repo.split("/", 1)[1],
                "url": "https://github.com/" + repo,
                "source": "github"
            }
            for repo in uniq
        ]
    except Exception:
        return []


def judge(item):
    score = 0
    title = (item.get("title") or "").lower()
    url = (item.get("url") or "").lower()
    text = title + " " + url

    if any(x in text for x in ["agent", "framework", "automation", "workflow", "tool", "mcp"]):
        score += 3

    if any(x in text for x in ["local", "ollama", "offline", "mlx", "llm", "codex", "openai", "claude"]):
        score += 2

    if any(x in text for x in ["github", "cli", "sdk"]):
        score += 1

    if any(x in text for x in ["telegram", "desktop", "screen", "sherlock"]):
        score -= 2

    if any(x in text for x in ["agent-framework", "goose", "onyx", "codex"]):
        score += 2

    if score >= 6:
        status = "adopt"
    elif score >= 3:
        status = "hold"
    else:
        status = "reject"

    return score, status

def save(items):
    with conn() as c:
        for i in items:
            score, status = judge(i)
            c.execute("""
            insert into adoption_candidates(title,url,source,score,status)
            values(?,?,?,?,?)
            """, (i["title"], i["url"], i["source"], score, status))
        c.commit()

def run_once():
    items = []
    items += fetch_github_trending()
    save(items)
    print(f"saved={len(items)}")

if __name__ == "__main__":
    run_once()
