#!/usr/bin/env python3
"""
Run this once to log into Facebook manually and save the session.
The saved auth_state.json is reused by all scrapers.
"""
import os
import time
from playwright.sync_api import sync_playwright

AUTH_STATE_PATH = os.environ.get("AUTH_STATE_PATH", "auth_state.json")

def login_and_save(output_path: str = AUTH_STATE_PATH):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        print("[login] Opening Facebook — log in manually in the browser window.")
        page.goto("https://www.facebook.com")

        input("[login] Press Enter once you are fully logged in and can see your feed...")

        # Extra wait so any post-login redirects settle
        time.sleep(2)

        context.storage_state(path=output_path)
        print(f"[login] Session saved to {output_path}")
        browser.close()


if __name__ == "__main__":
    login_and_save()
