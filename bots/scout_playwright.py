import asyncio
import sqlite3
from pathlib import Path
import sys
from playwright.async_api import async_playwright

sys.path.append(str(Path(__file__).resolve().parents[1]))
from oclibs.telegram import send as tg_send

DB = "data/openclaw.db"

TARGETS = [
    ("Kickstarter Gadgets", "https://www.kickstarter.com/discover/advanced?category_id=337"),
    ("Kickstarter Tech", "https://www.kickstarter.com/discover/advanced?category_id=16"),
    ("Kickstarter Design", "https://www.kickstarter.com/discover/advanced?category_id=28"),
]

def db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS seen(url TEXT PRIMARY KEY)")
    conn.commit()
    return conn, cur

def seen(cur, url: str) -> bool:
    cur.execute("SELECT 1 FROM seen WHERE url=?", (url,))
    return cur.fetchone() is not None

def save(cur, url: str):
    cur.execute("INSERT OR IGNORE INTO seen(url) VALUES(?)", (url,))

async def collect_projects(page):
    # 遅延ロード対策：少しスクロールして「増える」状態を作る
    await page.wait_for_timeout(3000)
    for _ in range(6):
        await page.mouse.wheel(0, 2500)
        await page.wait_for_timeout(1200)

    # KickstarterのプロジェクトURL（/projects/...）を直接取得
    links = await page.eval_on_selector_all(
        'a[href^="/projects/"]',
        "els => els.map(e => ({href:e.getAttribute('href'), text:(e.innerText||'').trim()}))"
    )

    items = []
    for x in links:
        href = x.get("href") or ""
        if not href.startswith("/projects/"):
            continue
        url = "https://www.kickstarter.com" + href.split("?")[0]
        title = (x.get("text") or "").split("\n")[0].strip()
        if not title:
            title = url.split("/")[-1]
        items.append((title, url))

    # 重複除去
    uniq = {}
    for t,u in items:
        uniq[u] = t
    return [(t,u) for u,t in uniq.items()]

def format_message(source_name: str, items):
    msg = f"🚀 <b>{source_name}</b> New candidates: {len(items)}\n\n"
    for title, url in items[:12]:
        msg += f"• {title}\n{url}\n\n"
    return msg

async def main():
    conn, cur = db()
    total_new = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        )

        for name, url in TARGETS:
            print("Opening:", url)
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            items = await collect_projects(page)
            print("Found project-like links:", len(items))

            new_items = []
            for title, link in items:
                if not seen(cur, link):
                    save(cur, link)
                    new_items.append((title, link))

            conn.commit()

            if new_items:
                total_new += len(new_items)
                tg_send(format_message(name, new_items))
            else:
                print("No new items for:", name)

        await browser.close()

    conn.close()
    if total_new == 0:
        print("No new items (all seen or nothing extracted).")

if __name__ == "__main__":
    asyncio.run(main())
