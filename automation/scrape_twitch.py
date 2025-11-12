from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

OUTPUT_DIR = Path("tmp")
OUTPUT_DIR.mkdir(exist_ok=True)

LOGIN_URL = os.getenv("PLAYWRIGHT_LOGIN_URL", "https://www.twitch.tv/login")
USERNAME = os.getenv("PLAYWRIGHT_USERNAME")
PASSWORD = os.getenv("PLAYWRIGHT_PASSWORD")
TARGET_URL = os.getenv("PLAYWRIGHT_TARGET_URL", "https://www.twitch.tv/")


async def run(dry_run: bool = False) -> None:
    if not USERNAME or not PASSWORD:
        raise RuntimeError("PLAYWRIGHT_USERNAME / PLAYWRIGHT_PASSWORD を .env に入れてください")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            # 1) ログインページへ
            await page.goto(LOGIN_URL, wait_until="networkidle", timeout=25_000)

            # 2) ユーザー名を入れる（あるもの全部に投げる）
            await page.fill("input#login-username, input[name='login'], input#username", USERNAME)

            # 3) パスワード欄を待ってから入れる
            await page.wait_for_selector(
                "input#password, input[name='password'], input[type='password']",
                timeout=15_000,
            )
            await page.fill(
                "input#password, input[name='password'], input[type='password']",
                PASSWORD,
            )

            # 4) ログインボタン
            await page.click(
                "button[data-a-target='passport-login-button'], "
                "button:has-text('Log In'), button:has-text('ログイン')"
            )

            # 5) ログイン後ページへ
            await page.goto(TARGET_URL, wait_until="networkidle", timeout=25_000)

            if dry_run:
                print("[DRY RUN] twitch login/page ok")
            else:
                html = await page.content()
                (OUTPUT_DIR / "twitch.html").write_text(html, encoding="utf-8")
                print("saved to tmp/twitch.html")

            await browser.close()
        except Exception as e:  # noqa: BLE001
            screenshot_path = OUTPUT_DIR / "twitch-error.png"
            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception:
                pass
            await browser.close()
            raise RuntimeError(f"Twitch scraping failed: {e}. screenshot={screenshot_path}") from e


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    asyncio.run(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
