from playwright.sync_api import sync_playwright
import random
import time

BASE = "https://chore-telegram-runtime-isola.openclaw-fortune.pages.dev"
variants = ["A", "B", "C"]

def run_variant(page, v: str, do_unlock: bool):
    page.goto(f"{BASE}/index_{v}.html", wait_until="networkidle")
    page.click(f'a[href="order.html?v={v}"]')
    page.wait_for_load_state("networkidle")

    page.fill('input[name="customer_name"]', f"browser_{random.randint(100000,999999)}")
    page.fill('input[name="birth_date"]', "1990-01-01")
    if page.locator('input[name="birth_time"]').count():
        page.fill('input[name="birth_time"]', "12:00")
    page.fill('textarea[name="question"]', "相手と今後どうなるか知りたいです")
    page.fill('input[name="email"]', f"browser_{random.randint(100000,999999)}@example.com")

    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    if do_unlock:
        if page.locator('a[href="unlock.html"]').count():
            page.click('a[href="unlock.html"]')
            page.wait_for_load_state("networkidle")
            if page.locator("#unlockBtn").count():
                page.click("#unlockBtn")
                page.wait_for_timeout(1500)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for v in variants:
        for i in range(10):
            page = browser.new_page()
            run_variant(page, v, do_unlock=(i < 3))
            page.close()
            time.sleep(0.5)
    browser.close()

print("browser_flow_done")
