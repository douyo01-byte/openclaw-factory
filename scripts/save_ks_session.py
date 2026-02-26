import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://www.kickstarter.com/"
STATE_PATH="configs/ks_storage_state.json"

async def main():
    Path("configs").mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(URL, timeout=60000, wait_until="domcontentloaded")

        print("Cloudflare/同意などを手で通してください。終わったらEnter。")
        input()

        await context.storage_state(path=STATE_PATH)
        print("saved:", STATE_PATH)
        await browser.close()

asyncio.run(main())
